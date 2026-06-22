"""Customer endpoints — RBAC-scoped CRUD with filters + pagination."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status

from app.core.deps import CurrentUser, DbDep
from app.models.enums import CustomerStatus
from app.schemas.common import Page
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerUpdate
from app.services import customer_service as svc

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=Page[CustomerOut])
async def list_customers(
    db: DbDep,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: CustomerStatus | None = None,
    q: str | None = None,
    owner_id: uuid.UUID | None = None,
) -> Page[CustomerOut]:
    items, total = await svc.list_customers(
        db, user, page=page, limit=limit, status_filter=status, q=q, owner_id=owner_id
    )
    return Page(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(data: CustomerCreate, db: DbDep, user: CurrentUser) -> CustomerOut:
    return await svc.create_customer(db, user, data)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(customer_id: uuid.UUID, db: DbDep, user: CurrentUser) -> CustomerOut:
    return await svc.get_customer(db, user, customer_id)


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: uuid.UUID, data: CustomerUpdate, db: DbDep, user: CurrentUser
) -> CustomerOut:
    return await svc.update_customer(db, user, customer_id, data)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(customer_id: uuid.UUID, db: DbDep, user: CurrentUser) -> Response:
    await svc.delete_customer(db, user, customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
