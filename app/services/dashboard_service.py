"""Dashboard aggregation, role-scoped. Results are cached by the router."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import AIInsight
from app.models.customer import Customer
from app.models.enums import CustomerStatus, Sentiment
from app.models.interaction import Interaction
from app.models.user import User
from app.services.customer_service import is_privileged


def scope_for(user: User) -> str:
    """Cache scope: privileged users share the org-wide view; csm is per-user."""
    return "all" if is_privileged(user) else f"user:{user.id}"


async def compute_metrics(db: AsyncSession, user: User) -> dict:
    cust_owner = None if is_privileged(user) else user.id

    # --- customers ---
    cust_q = select(Customer.status, func.count()).group_by(Customer.status)
    if cust_owner is not None:
        cust_q = cust_q.where(Customer.owner_id == cust_owner)
    by_status_rows = (await db.execute(cust_q)).all()
    customers_by_status = {s: 0 for s in (st.value for st in CustomerStatus)}
    for status_val, count in by_status_rows:
        key = status_val.value if hasattr(status_val, "value") else str(status_val)
        customers_by_status[key] = int(count)
    total_customers = sum(customers_by_status.values())
    at_risk_count = customers_by_status.get(CustomerStatus.at_risk.value, 0)

    # --- interactions (joined to customer for scoping) ---
    int_q = select(func.count()).select_from(Interaction).join(
        Customer, Interaction.customer_id == Customer.id
    )
    if cust_owner is not None:
        int_q = int_q.where(Customer.owner_id == cust_owner)
    total_interactions = int(await db.scalar(int_q) or 0)

    # --- sentiment breakdown (insights on in-scope interactions) ---
    sent_q = (
        select(AIInsight.sentiment, func.count())
        .join(Interaction, AIInsight.interaction_id == Interaction.id)
        .join(Customer, Interaction.customer_id == Customer.id)
        .group_by(AIInsight.sentiment)
    )
    if cust_owner is not None:
        sent_q = sent_q.where(Customer.owner_id == cust_owner)
    sentiment_breakdown = {s.value: 0 for s in Sentiment}
    for sent_val, count in (await db.execute(sent_q)).all():
        key = sent_val.value if hasattr(sent_val, "value") else str(sent_val)
        sentiment_breakdown[key] = int(count)

    # --- open risks (sum of risk-list lengths across in-scope insights) ---
    risks_q = (
        select(AIInsight.risks)
        .join(Interaction, AIInsight.interaction_id == Interaction.id)
        .join(Customer, Interaction.customer_id == Customer.id)
    )
    if cust_owner is not None:
        risks_q = risks_q.where(Customer.owner_id == cust_owner)
    open_risks_count = sum(len(r or []) for (r,) in (await db.execute(risks_q)).all())

    # --- interactions over time (last 14 days, grouped by day) ---
    since = datetime.now(timezone.utc) - timedelta(days=14)
    day = func.date(Interaction.meeting_date)
    ts_q = (
        select(day.label("d"), func.count())
        .join(Customer, Interaction.customer_id == Customer.id)
        .where(Interaction.meeting_date >= since)
        .group_by(day)
        .order_by(day)
    )
    if cust_owner is not None:
        ts_q = ts_q.where(Customer.owner_id == cust_owner)
    interactions_over_time = [
        {"date": str(d), "count": int(c)} for d, c in (await db.execute(ts_q)).all()
    ]

    # --- recent interactions (latest 5 in scope) ---
    recent_q = (
        select(Interaction, Customer.name, AIInsight.sentiment)
        .join(Customer, Interaction.customer_id == Customer.id)
        .outerjoin(AIInsight, AIInsight.interaction_id == Interaction.id)
        .order_by(Interaction.meeting_date.desc())
        .limit(5)
    )
    if cust_owner is not None:
        recent_q = recent_q.where(Customer.owner_id == cust_owner)
    recent_interactions = []
    for interaction, customer_name, sentiment in (await db.execute(recent_q)).all():
        recent_interactions.append(
            {
                "id": str(interaction.id),
                "title": interaction.title,
                "type": interaction.type.value,
                "customer_name": customer_name,
                "meeting_date": interaction.meeting_date.isoformat(),
                "sentiment": sentiment.value if sentiment is not None else None,
            }
        )

    return {
        "total_customers": total_customers,
        "customers_by_status": customers_by_status,
        "at_risk_count": at_risk_count,
        "total_interactions": total_interactions,
        "sentiment_breakdown": sentiment_breakdown,
        "open_risks_count": open_risks_count,
        "interactions_over_time": interactions_over_time,
        "recent_interactions": recent_interactions,
        "scope": scope_for(user),
        "cached": False,
    }
