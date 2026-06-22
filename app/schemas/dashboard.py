"""Dashboard metric schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class TimePoint(BaseModel):
    date: str
    count: int


class RecentInteraction(BaseModel):
    id: uuid.UUID
    title: str
    type: str
    customer_name: str
    meeting_date: str
    sentiment: str | None = None


class DashboardMetrics(BaseModel):
    total_customers: int
    customers_by_status: dict[str, int]
    at_risk_count: int
    total_interactions: int
    sentiment_breakdown: dict[str, int]
    open_risks_count: int
    interactions_over_time: list[TimePoint]
    recent_interactions: list[RecentInteraction]
    scope: str
    cached: bool = False
