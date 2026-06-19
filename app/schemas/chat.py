from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    message: str
    top_k: int = 3


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    chunks_used: int
