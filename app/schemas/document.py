import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    filename: str
    chunk_count: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
