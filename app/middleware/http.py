import logging
import time

import redis.asyncio as aioredis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

_redis = aioredis.from_url(settings.redis_url, decode_responses=True)

_RATE_LIMIT = 60  # requests per minute per API key


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000)
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("x-api-key")
        if api_key:
            bucket = int(time.time() // 60)
            key = f"ratelimit:{api_key}:{bucket}"
            count = await _redis.incr(key)
            if count == 1:
                await _redis.expire(key, 60)
            if count > _RATE_LIMIT:
                logger.warning("rate_limit_exceeded", extra={"key_prefix": api_key[:8]})
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Max 60 requests per minute."},
                )
        return await call_next(request)
