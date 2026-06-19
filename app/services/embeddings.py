from langchain_ollama import OllamaEmbeddings

from app.config import settings

_embedder = OllamaEmbeddings(
    model=settings.embedding_model,
    base_url=settings.ollama_base_url,
)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await _embedder.aembed_documents(texts)


async def embed_query(text: str) -> list[float]:
    return await _embedder.aembed_query(text)
