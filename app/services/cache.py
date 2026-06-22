"""Thin Redis cache helpers. Every call degrades gracefully if Redis is down."""
from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.redis_client import get_redis

DASHBOARD_PREFIX = "dashboard:metrics"


def dashboard_key(scope: str) -> str:
    return f"{DASHBOARD_PREFIX}:{scope}"


async def cache_get_json(key: str) -> Any | None:
    client = get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set_json(key: str, value: Any, ttl: int) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


async def invalidate_dashboard(owner_id: uuid.UUID | None = None) -> None:
    """Drop the org-wide cache and (if known) the affected owner's scoped cache.

    Called after any customer/interaction/insight write so the dashboard never
    serves stale data.
    """
    client = get_redis()
    if client is None:
        return
    keys = [dashboard_key("all")]
    if owner_id is not None:
        keys.append(dashboard_key(f"user:{owner_id}"))
    try:
        await client.delete(*keys)
    except Exception:
        pass
