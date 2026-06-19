from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import v1_router
from app.config import settings
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Tenant AI Agent",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.include_router(v1_router)
    return app


app = create_app()
