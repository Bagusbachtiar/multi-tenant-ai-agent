import asyncio
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.dependencies import hash_api_key
from app.models.tenant import Tenant
from app.services.chat import process_message

router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)

_WA_API = "https://graph.facebook.com/v18.0"
_processing: set[str] = set()


async def _get_whatsapp_tenant(db: AsyncSession) -> Tenant:
    key_hash = hash_api_key(settings.whatsapp_tenant_api_key)
    result = await db.execute(
        select(Tenant).where(Tenant.api_key_hash == key_hash, Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="WhatsApp tenant not configured")
    return tenant


async def _send_whatsapp(to: str, text: str) -> None:
    url = f"{_WA_API}/{settings.whatsapp_phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error("whatsapp_send_failed", extra={"status": resp.status_code, "body": resp.text})


async def _handle_message(message_id: str, phone: str, text_msg: str) -> None:
    if message_id in _processing:
        logger.info("whatsapp_duplicate_skipped", extra={"message_id": message_id})
        return
    _processing.add(message_id)
    try:
        async with AsyncSessionLocal() as db:
            key_hash = hash_api_key(settings.whatsapp_tenant_api_key)
            result = await db.execute(
                select(Tenant).where(Tenant.api_key_hash == key_hash, Tenant.is_active.is_(True))
            )
            tenant = result.scalar_one_or_none()
            if tenant is None:
                logger.error("whatsapp_tenant_not_found")
                return
            await db.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant.id)},
            )
            answer, _ = await process_message(
                tenant_id=str(tenant.id),
                session_id=phone,
                message=text_msg,
                db=db,
            )
        await _send_whatsapp(phone, answer)
    except Exception:
        logger.exception("whatsapp_handle_failed", extra={"phone": phone})
    finally:
        _processing.discard(message_id)


@router.get("/whatsapp-meta", response_class=PlainTextResponse)
async def meta_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> str:
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return hub_challenge
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/whatsapp-meta")
async def meta_incoming(
    request: Request,
    background_tasks: BackgroundTasks,
) -> PlainTextResponse:
    body = await request.json()

    try:
        value = body["entry"][0]["changes"][0]["value"]
        if not value.get("messages"):
            return PlainTextResponse("ok")

        message = value["messages"][0]
        if message["type"] not in ("text", "interactive"):
            return PlainTextResponse("ok")

        message_id = message["id"]
        phone = message["from"]
        text_msg = (
            message.get("text", {}).get("body")
            or message.get("interactive", {}).get("button_reply", {}).get("title")
            or ""
        ).strip()

        if not text_msg:
            return PlainTextResponse("ok")

    except (KeyError, IndexError):
        return PlainTextResponse("ok")

    # Return 200 immediately — prevents Meta from retrying due to slow LLM response
    background_tasks.add_task(_handle_message, message_id, phone, text_msg)
    return PlainTextResponse("ok")
