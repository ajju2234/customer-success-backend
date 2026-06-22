"""Dashboard endpoint — Redis cache-aside with TTL; invalidated on writes."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.schemas.dashboard import DashboardMetrics
from app.services.cache import cache_get_json, cache_set_json, dashboard_key
from app.services.dashboard_service import compute_metrics, scope_for

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger("dashboard")


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(db: DbDep, user: CurrentUser) -> DashboardMetrics:
    key = dashboard_key(scope_for(user))

    cached = await cache_get_json(key)
    if cached is not None:
        logger.info("dashboard cache HIT (%s)", key)
        cached["cached"] = True
        return DashboardMetrics(**cached)

    logger.info("dashboard cache MISS (%s)", key)
    metrics = await compute_metrics(db, user)
    await cache_set_json(key, metrics, settings.dashboard_cache_ttl_seconds)
    return DashboardMetrics(**metrics)
