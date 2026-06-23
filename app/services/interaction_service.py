"""Interaction business logic. Access is derived from the parent customer's ownership."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_insight import AIInsight
from app.models.customer import Customer
from app.models.enums import InteractionType, Role, Sentiment
from app.models.interaction import Interaction
from app.models.user import User
from app.schemas.interaction import InteractionCreate, InteractionUpdate
from app.services.cache import invalidate_dashboard
from app.services.customer_service import get_customer, is_privileged


async def _load(db: AsyncSession, interaction_id: uuid.UUID) -> Interaction | None:
    result = await db.execute(
        select(Interaction)
        .options(selectinload(Interaction.insight), selectinload(Interaction.customer))
        .where(Interaction.id == interaction_id)
    )
    return result.scalar_one_or_none()


async def get_interaction(db: AsyncSession, user: User, interaction_id: uuid.UUID) -> Interaction:
    interaction = await _load(db, interaction_id)
    if interaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interaction not found")
    # Reuse the customer ownership check (raises 403/404 as appropriate).
    await get_customer(db, user, interaction.customer_id)
    return interaction


async def list_interactions(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    limit: int = 20,
    customer_id: uuid.UUID | None = None,
    type_filter: InteractionType | None = None,
    sentiment: Sentiment | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[Interaction], int]:
    base = select(Interaction).join(Customer, Interaction.customer_id == Customer.id)
    conditions = []
    if not is_privileged(user):
        conditions.append(Customer.owner_id == user.id)
    if customer_id is not None:
        conditions.append(Interaction.customer_id == customer_id)
    if type_filter is not None:
        conditions.append(Interaction.type == type_filter)
    if date_from is not None:
        conditions.append(Interaction.meeting_date >= date_from)
    if date_to is not None:
        conditions.append(Interaction.meeting_date <= date_to)
    if sentiment is not None:
        base = base.join(AIInsight, AIInsight.interaction_id == Interaction.id)
        conditions.append(AIInsight.sentiment == sentiment)

    if conditions:
        base = base.where(*conditions)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rows = await db.execute(
        base.options(selectinload(Interaction.insight), selectinload(Interaction.customer))
        .order_by(Interaction.meeting_date.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(rows.scalars().unique().all()), int(total or 0)


async def create_interaction(
    db: AsyncSession, user: User, data: InteractionCreate
) -> Interaction:
    customer = await get_customer(db, user, data.customer_id)  # access check
    interaction = Interaction(**data.model_dump(), user_id=user.id)
    db.add(interaction)
    await db.flush()
    # Generate AI insight when notes are provided (never blocks/breaks the create).
    if interaction.notes and interaction.notes.strip():
        from app.services.insight_service import generate_and_store

        await generate_and_store(db, interaction)
    await invalidate_dashboard(customer.owner_id)
    return await _load(db, interaction.id)  # eager-load `insight` for serialization


async def update_interaction(
    db: AsyncSession, user: User, interaction_id: uuid.UUID, data: InteractionUpdate
) -> Interaction:
    interaction = await get_interaction(db, user, interaction_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(interaction, field, value)
    await db.flush()
    customer = await db.get(Customer, interaction.customer_id)
    await invalidate_dashboard(customer.owner_id if customer else None)
    return await _load(db, interaction.id)


async def delete_interaction(db: AsyncSession, user: User, interaction_id: uuid.UUID) -> None:
    interaction = await get_interaction(db, user, interaction_id)
    customer = await db.get(Customer, interaction.customer_id)
    owner_id = customer.owner_id if customer else None
    await db.delete(interaction)
    await db.flush()
    await invalidate_dashboard(owner_id)
