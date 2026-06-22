"""Authentication endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.core.security import (
    REFRESH,
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth_service import authenticate, register_user

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # set True behind HTTPS in production
        max_age=settings.refresh_token_expire_days * 24 * 3600,
        path="/",
    )


def _issue_tokens(response: Response, user: User) -> TokenResponse:
    access = create_access_token(str(user.id), user.role.value)
    refresh = create_refresh_token(str(user.id), user.role.value)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, response: Response, db: DbDep) -> TokenResponse:
    user = await register_user(db, data)
    return _issue_tokens(response, user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: DbDep) -> TokenResponse:
    user = await authenticate(db, data.email, data.password)
    return _issue_tokens(response, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: DbDep,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    if payload.get("type") != REFRESH:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return _issue_tokens(response, user)  # rotate refresh token


@router.post("/logout")
async def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(REFRESH_COOKIE, path="/")
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
