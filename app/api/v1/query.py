from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_tenant, get_tenant_db
from app.models.document import Chunk
from app.models.tenant import Tenant
from app.schemas.query import ChunkResult, QueryRequest, QueryResponse
from app.services.embeddings import embed_query
from app.services.llm import generate

router = APIRouter(prefix="/query", tags=["query"])

_PROMPT_TEMPLATE = """\
You are a helpful assistant. Answer using only the context below.

Context:
{context}

Question: {question}
Answer:"""


@router.post("", response_model=QueryResponse)
async def query_documents(
    body: QueryRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> QueryResponse:
    vec = await embed_query(body.question)

    distance_col = Chunk.embedding.cosine_distance(vec).label("distance")
    stmt = (
        select(Chunk.chunk_index, Chunk.content, distance_col)
        .where(Chunk.embedding.isnot(None))
        .order_by(distance_col)
        .limit(body.top_k)
    )
    rows = (await db.execute(stmt)).all()

    chunk_results = [
        ChunkResult(chunk_index=row.chunk_index, content=row.content, distance=row.distance)
        for row in rows
    ]

    context = "\n---\n".join(r.content for r in chunk_results)
    prompt = _PROMPT_TEMPLATE.format(context=context, question=body.question)
    answer = await generate(prompt)

    return QueryResponse(question=body.question, chunks=chunk_results, prompt=prompt, answer=answer)
