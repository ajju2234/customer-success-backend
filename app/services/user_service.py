"""User administration (admin-only): list users and update role / active status."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Role
from app.models.user import User
from app.schemas.auth import UserUpdate


async def list_users(
    db: AsyncSession,
    *,
    page: int = 1,
    limit: int = 20,
    q: str | None = None,
    role: Role | None = None,
) -> tuple[list[User], int]:
    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append(or_(User.name.ilike(like), User.email.ilike(like)))
    if role is not None:
        conditions.append(User.role == role)

    base = select(User)
    if conditions:
        base = base.where(*conditions)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rows = await db.execute(
        base.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    return list(rows.scalars().all()), int(total or 0)


async def update_user(
    db: AsyncSession, current_user: User, user_id: uuid.UUID, data: UserUpdate
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Guard: an admin cannot lock themselves out (demote or deactivate own account).
    if user.id == current_user.id:
        if data.role is not None and data.role != Role.admin:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")
        if data.is_active is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself")

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    await db.flush()
    await db.refresh(user)
    return user
