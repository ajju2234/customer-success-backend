"""Single shared async Redis client, created at app startup and closed at shutdown."""
from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    global _client
    _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_redis() -> redis.Redis | None:
    """Return the shared client (or None if Redis is unavailable / not initialised)."""
    return _client
