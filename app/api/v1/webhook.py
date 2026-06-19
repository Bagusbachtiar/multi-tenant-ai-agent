from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_tenant, get_tenant_db
from app.models.tenant import Tenant
from app.schemas.webhook import WhatsAppIncoming, WhatsAppReply
from app.services.chat import process_message

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/whatsapp", response_model=WhatsAppReply)
async def whatsapp_webhook(
    body: WhatsAppIncoming,
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_tenant_db)],
    x_webhook_secret: Annotated[str | None, Header()] = None,
) -> WhatsAppReply:
    if settings.n8n_webhook_secret and x_webhook_secret != settings.n8n_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    answer, _ = await process_message(
        tenant_id=str(tenant.id),
        session_id=body.from_number,
        message=body.message,
        db=db,
    )
    return WhatsAppReply(reply=answer, session_id=body.from_number)
