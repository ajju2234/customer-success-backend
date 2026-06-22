"""AI insight schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InsightStatus, Sentiment


class InsightData(BaseModel):
    """The structured payload we require the LLM to return (and validate)."""

    summary: str = Field(min_length=1)
    sentiment: Sentiment
    action_items: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interaction_id: uuid.UUID
    summary: str
    sentiment: Sentiment
    action_items: list[str]
    risks: list[str]
    model: str | None
    status: InsightStatus
    created_at: datetime
