import json

import redis.asyncio as aioredis

from app.config import settings

_redis = aioredis.from_url(settings.redis_url, decode_responses=True)

_KEY_PREFIX = "chat"
_TTL = 86400  # 24 hours
_MAX_MESSAGES = 10  # keep last 10 messages (5 turns)


async def load_history(tenant_id: str, session_id: str) -> list[dict]:
    key = f"{_KEY_PREFIX}:{tenant_id}:{session_id}"
    data = await _redis.get(key)
    return json.loads(data) if data else []


async def save_history(tenant_id: str, session_id: str, messages: list[dict]) -> None:
    key = f"{_KEY_PREFIX}:{tenant_id}:{session_id}"
    await _redis.set(key, json.dumps(messages[-_MAX_MESSAGES:]), ex=_TTL)


def format_history(messages: list[dict]) -> str:
    if not messages:
        return ""
    lines = []
    for msg in messages:
        role = "Human" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines) + "\n"
