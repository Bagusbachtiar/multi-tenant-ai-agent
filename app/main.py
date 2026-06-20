import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import v1_router
from app.config import settings
from app.database import engine
from app.logging_config import setup_logging
from app.middleware.http import RateLimitMiddleware, RequestLoggingMiddleware

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"env": settings.app_env})
    yield
    await engine.dispose()
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Tenant AI Agent",
        version="0.1.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", exc_info=exc, extra={"path": str(request.url)})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(v1_router)
    return app


app = create_app()
