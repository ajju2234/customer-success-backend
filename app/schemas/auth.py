"""Auth + user schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # Role is selectable at registration for demo/testing convenience. In a real
    # system, role assignment would be an admin-only operation.
    role: Role = Role.csm


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Admin-only updates to another user's role / active status."""

    role: Role | None = None
    is_active: bool | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    # Demo only: email delivery isn't wired up, so the reset token is returned
    # directly. In production this would be emailed as a link and never returned.
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
