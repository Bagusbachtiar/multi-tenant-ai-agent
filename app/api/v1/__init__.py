from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.documents import router as documents_router
from app.api.v1.health import router as health_router
from app.api.v1.query import router as query_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.webhook import router as webhook_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router, tags=["health"])
v1_router.include_router(tenants_router)
v1_router.include_router(documents_router)
v1_router.include_router(query_router)
v1_router.include_router(chat_router)
v1_router.include_router(webhook_router)
