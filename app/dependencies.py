import hashlib
import secrets
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, hashed_key). Store hash only; return raw once at creation."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_api_key(raw)


async def get_current_tenant(
    x_api_key: Annotated[str, Header()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    key_hash = hash_api_key(x_api_key)
    result = await db.execute(
        select(Tenant).where(
            Tenant.api_key_hash == key_hash,
            Tenant.is_active.is_(True),
        )
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return tenant


async def get_tenant_db(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[AsyncSession, None]:
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant.id)},
    )
    yield db
