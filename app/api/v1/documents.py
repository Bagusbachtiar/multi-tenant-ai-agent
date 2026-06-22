import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_tenant, get_tenant_db
from app.models.document import Chunk, Document
from app.models.tenant import Tenant
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/documents", tags=["documents"])

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# Matches === SECTION HEADER === pattern (structured menus, FAQs, docs)
_SECTION_PATTERN = re.compile(r"(?=^===\s+)", re.MULTILINE)


def _split_text(text: str) -> list[str]:
    # If doc has === section headers, split on them — keeps each section intact
    if "===" in text:
        raw = _SECTION_PATTERN.split(text)
        chunks = [s.strip() for s in raw if s.strip()]
        if len(chunks) > 1:
            return chunks
    # Fallback: recursive character split
    return _splitter.split_text(text)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> DocumentResponse:
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded text",
        )

    texts = _split_text(text)
    if not texts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document produced no chunks after splitting",
        )

    vectors = await embed_texts(texts)

    doc = Document(tenant_id=tenant.id, filename=file.filename or "untitled")
    db.add(doc)
    await db.flush()

    chunks = [
        Chunk(
            document_id=doc.id,
            tenant_id=tenant.id,
            chunk_index=i,
            content=chunk_text,
            embedding=vectors[i],
        )
        for i, chunk_text in enumerate(texts)
    ]
    db.add_all(chunks)
    await db.commit()

    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        chunk_count=len(chunks),
        created_at=doc.created_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> DocumentListResponse:
    stmt = select(
        Document.id,
        Document.filename,
        Document.created_at,
        func.count(Chunk.id).label("chunk_count"),
    ).outerjoin(Chunk, Chunk.document_id == Document.id).group_by(Document.id).order_by(Document.created_at.desc())

    rows = (await db.execute(stmt)).all()
    docs = [
        DocumentResponse(id=r.id, filename=r.filename, chunk_count=r.chunk_count, created_at=r.created_at)
        for r in rows
    ]
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> None:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await db.delete(doc)
    await db.commit()
