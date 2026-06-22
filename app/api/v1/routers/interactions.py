"""Interaction endpoints — CRUD with filters + pagination."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, Response, status

from app.core.deps import CurrentUser, DbDep
from app.models.enums import InteractionType, Sentiment
from app.schemas.common import Page
from app.schemas.insight import InsightOut
from app.schemas.interaction import InteractionCreate, InteractionOut, InteractionUpdate
from app.services import interaction_service as svc
from app.services.insight_service import regenerate_for_interaction

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("", response_model=Page[InteractionOut])
async def list_interactions(
    db: DbDep,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    customer_id: uuid.UUID | None = None,
    type: InteractionType | None = None,
    sentiment: Sentiment | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Page[InteractionOut]:
    items, total = await svc.list_interactions(
        db, user, page=page, limit=limit, customer_id=customer_id,
        type_filter=type, sentiment=sentiment, date_from=date_from, date_to=date_to,
    )
    return Page(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=InteractionOut, status_code=status.HTTP_201_CREATED)
async def create_interaction(
    data: InteractionCreate, db: DbDep, user: CurrentUser
) -> InteractionOut:
    return await svc.create_interaction(db, user, data)


@router.get("/{interaction_id}", response_model=InteractionOut)
async def get_interaction(
    interaction_id: uuid.UUID, db: DbDep, user: CurrentUser
) -> InteractionOut:
    return await svc.get_interaction(db, user, interaction_id)


@router.patch("/{interaction_id}", response_model=InteractionOut)
async def update_interaction(
    interaction_id: uuid.UUID, data: InteractionUpdate, db: DbDep, user: CurrentUser
) -> InteractionOut:
    return await svc.update_interaction(db, user, interaction_id, data)


@router.delete("/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interaction(
    interaction_id: uuid.UUID, db: DbDep, user: CurrentUser
) -> Response:
    await svc.delete_interaction(db, user, interaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interaction_id}/insights", response_model=InsightOut, status_code=status.HTTP_201_CREATED)
async def regenerate_insight(
    interaction_id: uuid.UUID, db: DbDep, user: CurrentUser
) -> InsightOut:
    """(Re)generate the AI insight for an interaction."""
    return await regenerate_for_interaction(db, user, interaction_id)
