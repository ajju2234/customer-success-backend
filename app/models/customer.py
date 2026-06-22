"""Customer model."""
from __future__ import annotations

import uuid

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import CustomerStatus


class Customer(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (Index("ix_customers_owner_status", "owner_id", "status"),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, name="customer_status", values_callable=lambda e: [m.value for m in e]),
        default=CustomerStatus.prospect,
        nullable=False,
    )
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    owner: Mapped["User"] = relationship(back_populates="customers")  # noqa: F821
    interactions: Mapped[list["Interaction"]] = relationship(  # noqa: F821
        back_populates="customer", cascade="all, delete-orphan"
    )
