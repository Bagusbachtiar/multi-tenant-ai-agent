from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_tenant, get_tenant_db
from app.models.document import Chunk, Document
from app.models.tenant import Tenant
from app.schemas.document import DocumentResponse
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/documents", tags=["documents"])

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


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

    texts = _splitter.split_text(text)
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
