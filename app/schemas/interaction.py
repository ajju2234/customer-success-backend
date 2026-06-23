"""Interaction schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InteractionType
from app.schemas.insight import InsightOut


class InteractionCreate(BaseModel):
    customer_id: uuid.UUID
    type: InteractionType = InteractionType.meeting
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = None
    meeting_date: datetime


class InteractionUpdate(BaseModel):
    type: InteractionType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    meeting_date: datetime | None = None


class InteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None = None
    user_id: uuid.UUID | None
    type: InteractionType
    title: str
    notes: str | None
    meeting_date: datetime
    created_at: datetime
    updated_at: datetime
    insight: InsightOut | None = None
