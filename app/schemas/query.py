from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=10)


class ChunkResult(BaseModel):
    chunk_index: int
    content: str
    distance: float


class QueryResponse(BaseModel):
    question: str
    chunks: list[ChunkResult]
    prompt: str
    answer: str
