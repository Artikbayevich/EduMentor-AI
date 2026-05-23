"""
api/v1/endpoints/auth.py — HEMIS OAuth2 + JWT auth endpoints.

GET  /auth/hemis            → redirect to HEMIS authorize URL
GET  /auth/hemis/callback   → exchange code for tokens, upsert user, return JWT
POST /auth/refresh          → refresh access token from refresh token
POST /auth/logout           → revoke HEMIS token (best-effort)
GET  /auth/me               → current user profile (JWT protected)
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
)
from api.deps import get_current_active_user
from models.user import User, UserRole
from schemas.user import Token, UserResponse
from services.hemis.hemis_auth import (
    get_auth_url,
    exchange_code_for_token,
    refresh_token as hemis_refresh,
    revoke_token as hemis_revoke,
    HEMISAuthError,
    HEMISUnavailableError,
)
from services.hemis import make_hemis_client
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── In-memory PKCE state store (use Redis in production) ─────────────────────
# state_token → {"code_verifier": str, "telegram_id": int | None}
_pending_states: dict[str, dict] = {}


# ── Schemas ───────────────────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class AuthCallbackResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"
    user:          UserResponse


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/hemis",
    summary="Redirect to HEMIS OAuth2 authorization",
    response_class=RedirectResponse,
    status_code=302,
)
async def hemis_login(
    telegram_id: int | None = Query(None, description="Telegram user ID for bot linking"),
    redirect_after: str     = Query("/dashboard", description="Frontend path to redirect after login"),
) -> RedirectResponse:
    """
    Build HEMIS OAuth2 URL and redirect the browser.
    Stores PKCE verifier in memory keyed by `state`.
    """
    auth_url, state, verifier = get_auth_url(
        redirect_uri=settings.HEMIS_REDIRECT_URI,
        use_pkce=True,
    )
    _pending_states[state] = {
        "code_verifier": verifier,
        "telegram_id":   telegram_id,
        "redirect_after": redirect_after,
    }
    return RedirectResponse(url=auth_url)


@router.get(
    "/hemis/callback",
    response_model=AuthCallbackResponse,
    summary="HEMIS OAuth2 callback — exchanges code for tokens and upserts user",
)
async def hemis_callback(
    code:  str = Query(..., description="Authorization code from HEMIS"),
    state: str = Query(..., description="State token for CSRF / PKCE verification"),
    db: AsyncSession = Depends(get_db),
) -> AuthCallbackResponse:
    pending = _pending_states.pop(state, None)
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state. Please restart the login flow.",
        )

    verifier    = pending["code_verifier"]
    telegram_id = pending.get("telegram_id")

    # Exchange code → HEMIS tokens
    try:
        hemis_tokens = await exchange_code_for_token(
            code=code,
            redirect_uri=settings.HEMIS_REDIRECT_URI,
            code_verifier=verifier,
        )
    except HEMISAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except HEMISUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HEMIS is temporarily unavailable. Try again later.",
        )

    access_token_hemis = hemis_tokens["access_token"]

    # Fetch student info from HEMIS
    try:
        async with make_hemis_client(access_token_hemis) as client:
            info = await client.get_student_info()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch student info: {exc}",
        )

    # Upsert user in our DB
    svc  = UserService(db)
    user = await svc.get_by_email(info["hemis_id"] + "@hemis.uz")

    if user is None:
        from schemas.user import UserCreate
        user = await svc.create(
            UserCreate(
                email=info["hemis_id"] + "@hemis.uz",
                username=info["hemis_id"],
                full_name=info["full_name"],
                password=get_password_hash(info["hemis_id"] + settings.SECRET_KEY),
                role=UserRole.student,
            )
        )

    # Attach telegram_id if provided
    if telegram_id and user.telegram_id != telegram_id:
        user.telegram_id = telegram_id
        await db.flush()

    # Store extra profile fields not on User model via update
    await db.refresh(user)

    # Issue our own JWTs
    our_access  = create_access_token(str(user.id))
    our_refresh = create_refresh_token(str(user.id))

    return AuthCallbackResponse(
        access_token=our_access,
        refresh_token=our_refresh,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
)
async def refresh_access_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected a refresh token.",
        )
    user_id = payload.get("sub")
    svc     = UserService(db)
    user    = await svc.get_by_id(uuid.UUID(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post(
    "/logout",
    summary="Logout — revokes HEMIS token (best-effort)",
)
async def logout(
    body: LogoutRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    if body.refresh_token:
        await hemis_revoke(body.refresh_token)
    return {"message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Current authenticated user profile",
)
async def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
