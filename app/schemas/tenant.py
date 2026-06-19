import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class TenantCreateResponse(TenantResponse):
    api_key: str  # raw key — returned once only, never stored
