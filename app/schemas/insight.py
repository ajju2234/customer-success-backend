"""AI insight schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import InsightStatus, Sentiment


class InsightData(BaseModel):
    """The structured payload we require the LLM to return (and validate).

    Validators make parsing tolerant of LLM quirks (capitalised sentiment,
    null/None lists) so a usable answer doesn't get discarded as a "failure".
    """

    summary: str = Field(min_length=1)
    sentiment: Sentiment
    action_items: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

    @field_validator("sentiment", mode="before")
    @classmethod
    def _normalize_sentiment(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip().lower()
            if v not in ("positive", "neutral", "negative"):
                return "neutral"
        return v

    @field_validator("action_items", "risks", mode="before")
    @classmethod
    def _coerce_list(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return v


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
