"""Persist AI insights for interactions (generate-on-create + regenerate)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import AIInsight
from app.models.interaction import Interaction
from app.models.user import User
from app.services.ai_service import generate_insights


async def generate_and_store(db: AsyncSession, interaction: Interaction) -> AIInsight:
    """Run the AI pipeline for an interaction and upsert its insight row."""
    result = await generate_insights(interaction.notes or "")

    # Query the existing insight explicitly (avoids a lazy relationship load in async).
    insight = await db.scalar(
        select(AIInsight).where(AIInsight.interaction_id == interaction.id)
    )
    if insight is None:
        insight = AIInsight(interaction_id=interaction.id)
        db.add(insight)

    insight.summary = result.data.summary
    insight.sentiment = result.data.sentiment
    insight.action_items = result.data.action_items
    insight.risks = result.data.risks
    insight.model = result.model
    insight.status = result.status
    insight.raw_response = result.raw

    await db.flush()
    return insight


async def regenerate_for_interaction(
    db: AsyncSession, user: User, interaction_id: uuid.UUID
) -> AIInsight:
    # Local import avoids a circular import at module load time.
    from app.services.interaction_service import get_interaction
    from app.services.cache import invalidate_dashboard
    from app.models.customer import Customer

    interaction = await get_interaction(db, user, interaction_id)  # access check
    insight = await generate_and_store(db, interaction)
    customer = await db.get(Customer, interaction.customer_id)
    await invalidate_dashboard(customer.owner_id if customer else None)
    return insight
