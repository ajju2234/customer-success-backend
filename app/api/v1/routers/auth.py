"""Authentication endpoints."""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbDep
from app.core.email import reset_password_email, send_email
from app.core.security import (
    REFRESH,
    JWTError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services.auth_service import (
    authenticate,
    create_password_reset,
    register_user,
    reset_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("auth")

REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        samesite=settings.cookie_samesite,  # "none" for cross-domain prod
        secure=settings.cookie_secure,  # True behind HTTPS in production
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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(data: ForgotPasswordRequest, db: DbDep) -> ForgotPasswordResponse:
    token = await create_password_reset(db, data.email)
    demo_token: str | None = None

    if token:
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        if settings.email_enabled:
            try:
                await send_email(data.email, "Reset your password", reset_password_email(reset_url))
            except Exception:  # pragma: no cover - don't leak SMTP errors to the client
                logger.exception("Failed to send password-reset email")
        else:
            # No SMTP configured (e.g. local dev) → return the token so the flow still works.
            demo_token = token

    # Generic message either way so we don't reveal which emails are registered.
    return ForgotPasswordResponse(
        message="If that email is registered, a password reset link has been sent.",
        reset_token=demo_token,
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password_endpoint(data: ResetPasswordRequest, db: DbDep) -> Response:
    await reset_password(db, data.token, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
