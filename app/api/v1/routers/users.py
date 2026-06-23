"""User administration endpoints — admin only."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbDep, require_roles
from app.models.enums import Role
from app.schemas.auth import UserOut, UserUpdate
from app.schemas.common import Page
from app.services import user_service as svc

# Every route here requires the admin role.
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(require_roles(Role.admin))],
)


@router.get("", response_model=Page[UserOut])
async def list_users(
    db: DbDep,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = None,
    role: Role | None = None,
) -> Page[UserOut]:
    items, total = await svc.list_users(db, page=page, limit=limit, q=q, role=role)
    return Page(items=items, total=total, page=page, limit=limit)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID, data: UserUpdate, db: DbDep, current_user: CurrentUser
) -> UserOut:
    return await svc.update_user(db, current_user, user_id, data)
