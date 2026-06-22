"""Customer business logic: RBAC-scoped CRUD with filtering + pagination."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.enums import CustomerStatus, Role
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.cache import invalidate_dashboard


def is_privileged(user: User) -> bool:
    """admin/manager see and manage everything; csm is scoped to its own rows."""
    return user.role in (Role.admin, Role.manager)


async def list_customers(
    db: AsyncSession,
    user: User,
    *,
    page: int = 1,
    limit: int = 20,
    status_filter: CustomerStatus | None = None,
    q: str | None = None,
    owner_id: uuid.UUID | None = None,
) -> tuple[list[Customer], int]:
    conditions = []
    if not is_privileged(user):
        conditions.append(Customer.owner_id == user.id)  # csm: own only
    elif owner_id is not None:
        conditions.append(Customer.owner_id == owner_id)  # privileged filter

    if status_filter is not None:
        conditions.append(Customer.status == status_filter)
    if q:
        like = f"%{q}%"
        conditions.append(
            or_(Customer.name.ilike(like), Customer.company.ilike(like), Customer.email.ilike(like))
        )

    base = select(Customer)
    if conditions:
        base = base.where(*conditions)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rows = await db.execute(
        base.order_by(Customer.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    return list(rows.scalars().all()), int(total or 0)


async def get_customer(db: AsyncSession, user: User, customer_id: uuid.UUID) -> Customer:
    customer = await db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    if not is_privileged(user) and customer.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your customer")
    return customer


async def create_customer(db: AsyncSession, user: User, data: CustomerCreate) -> Customer:
    customer = Customer(**data.model_dump(), owner_id=user.id)
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    await invalidate_dashboard(customer.owner_id)
    return customer


async def update_customer(
    db: AsyncSession, user: User, customer_id: uuid.UUID, data: CustomerUpdate
) -> Customer:
    customer = await get_customer(db, user, customer_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    await db.flush()
    await db.refresh(customer)
    await invalidate_dashboard(customer.owner_id)
    return customer


async def delete_customer(db: AsyncSession, user: User, customer_id: uuid.UUID) -> None:
    customer = await get_customer(db, user, customer_id)
    owner_id = customer.owner_id
    await db.delete(customer)
    await db.flush()
    await invalidate_dashboard(owner_id)
