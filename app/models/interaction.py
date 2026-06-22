"""Interaction (meeting / call / email / note) model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import InteractionType


class Interaction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "interactions"
    __table_args__ = (Index("ix_interactions_customer_date", "customer_id", "meeting_date"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="interaction_type", values_callable=lambda e: [m.value for m in e]),
        default=InteractionType.meeting,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="interactions")  # noqa: F821
    insight: Mapped["AIInsight | None"] = relationship(  # noqa: F821
        back_populates="interaction", uselist=False, cascade="all, delete-orphan"
    )
