"""AI insight model — 1:1 with an interaction."""
from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import InsightStatus, Sentiment

# JSONB on Postgres, plain JSON on SQLite (used by the test suite).
JSONType = JSONB().with_variant(JSON(), "sqlite")


class AIInsight(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ai_insights"

    interaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("interactions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[Sentiment] = mapped_column(
        Enum(Sentiment, name="sentiment", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    action_items: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    risks: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[InsightStatus] = mapped_column(
        Enum(InsightStatus, name="insight_status", values_callable=lambda e: [m.value for m in e]),
        default=InsightStatus.success,
        nullable=False,
    )
    raw_response: Mapped[dict | None] = mapped_column(JSONType, nullable=True)

    interaction: Mapped["Interaction"] = relationship(back_populates="insight")  # noqa: F821
