from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Chunk
from app.services.embeddings import embed_query
from app.services.llm import generate
from app.services.session import format_history, load_history, save_history

_PROMPT_TEMPLATE = """\
You are a helpful assistant. Answer using only the context below.

Context:
{context}

{history}Human: {question}
Assistant:"""


async def process_message(
    tenant_id: str,
    session_id: str,
    message: str,
    db: AsyncSession,
    top_k: int = 3,
) -> tuple[str, int]:
    history = await load_history(tenant_id, session_id)
    vec = await embed_query(message)

    distance_col = Chunk.embedding.cosine_distance(vec).label("distance")
    stmt = (
        select(Chunk.content, distance_col)
        .where(Chunk.embedding.isnot(None))
        .order_by(distance_col)
        .limit(top_k)
    )
    rows = (await db.execute(stmt)).all()

    context = "\n---\n".join(row.content for row in rows)
    prompt = _PROMPT_TEMPLATE.format(
        context=context,
        history=format_history(history),
        question=message,
    )

    answer = await generate(prompt)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})
    await save_history(tenant_id, session_id, history)

    return answer, len(rows)
