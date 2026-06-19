from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_tenant, get_tenant_db
from app.models.tenant import Tenant
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import process_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
) -> ChatResponse:
    answer, chunks_used = await process_message(
        tenant_id=str(tenant.id),
        session_id=body.session_id,
        message=body.message,
        db=db,
        top_k=body.top_k,
    )
    return ChatResponse(session_id=body.session_id, answer=answer, chunks_used=chunks_used)
