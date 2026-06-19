from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import generate_api_key, get_current_tenant
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantCreateResponse, TenantResponse

router = APIRouter(prefix="/tenants", tags=["tenants"])


def require_admin(x_admin_key: Annotated[str, Header()]) -> None:
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


@router.post("", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_admin)],
) -> TenantCreateResponse:
    raw_key, key_hash = generate_api_key()
    tenant = Tenant(name=body.name, slug=body.slug, api_key_hash=key_hash)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return TenantCreateResponse(**TenantResponse.model_validate(tenant).model_dump(), api_key=raw_key)


@router.get("/me", response_model=TenantResponse)
async def get_me(
    tenant: Annotated[Tenant, Depends(get_current_tenant)],
) -> Tenant:
    return tenant
