"""Customer schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import CustomerStatus


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    status: CustomerStatus = CustomerStatus.prospect
    health_score: int | None = Field(default=None, ge=0, le=100)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    status: CustomerStatus | None = None
    health_score: int | None = Field(default=None, ge=0, le=100)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    company: str | None
    email: EmailStr | None
    phone: str | None
    status: CustomerStatus
    health_score: int | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
