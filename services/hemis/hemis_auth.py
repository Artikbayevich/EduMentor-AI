import hashlib
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from core.config import settings


# ─── Constants ────────────────────────────────────────────────────────────────

AUTHORIZE_URL = "https://student.hemis.uz/oauth/authorize"
TOKEN_URL = "https://student.hemis.uz/oauth/access-token"
TOKEN_TIMEOUT = httpx.Timeout(10.0)


# ─── PKCE helpers ─────────────────────────────────────────────────────────────

def _generate_code_verifier() -> str:
    """RFC 7636 – 43-128 char URL-safe random string."""
    return secrets.token_urlsafe(64)


def _generate_code_challenge(verifier: str) -> str:
    """S256 method: BASE64URL(SHA256(verifier))."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return (
        __import__("base64")
        .urlsafe_b64encode(digest)
        .rstrip(b"=")
        .decode()
    )


# ─── Auth URL ─────────────────────────────────────────────────────────────────

def get_auth_url(
    redirect_uri: str,
    state: str | None = None,
    *,
    use_pkce: bool = True,
) -> tuple[str, str | None, str | None]:
    """
    Build the HEMIS OAuth2 authorization URL.

    Returns:
        (url, state, code_verifier)
        code_verifier is None when use_pkce=False.
    """
    state = state or secrets.token_urlsafe(16)
    code_verifier: str | None = None

    params: dict[str, str] = {
        "client_id": settings.HEMIS_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
    }

    if use_pkce:
        code_verifier = _generate_code_verifier()
        params["code_challenge"] = _generate_code_challenge(code_verifier)
        params["code_challenge_method"] = "S256"

    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    logger.debug("Built HEMIS auth URL state={}", state)
    return url, state, code_verifier


# ─── Token exchange ───────────────────────────────────────────────────────────

async def exchange_code_for_token(
    code: str,
    redirect_uri: str,
    code_verifier: str | None = None,
) -> dict[str, Any]:
    """
    Exchange an authorization code for access + refresh tokens.

    Returns raw token payload:
        {
            "access_token": str,
            "refresh_token": str,
            "token_type": "Bearer",
            "expires_in": int,        # seconds
            "scope": str,
        }
    Raises:
        HEMISAuthError on non-200 or missing fields.
    """
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.HEMIS_CLIENT_ID,
        "client_secret": settings.HEMIS_CLIENT_SECRET,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier

    try:
        async with httpx.AsyncClient(timeout=TOKEN_TIMEOUT) as client:
            response = await client.post(TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("HEMIS token exchange failed: {} {}", exc.response.status_code, exc.response.text)
        raise HEMISAuthError(
            f"Token exchange failed: {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        logger.error("HEMIS unreachable during token exchange: {}", exc)
        raise HEMISUnavailableError("HEMIS is unreachable") from exc

    _validate_token_response(data)
    logger.info("HEMIS token exchange successful")
    return _enrich_token(data)


# ─── Token refresh ────────────────────────────────────────────────────────────

async def refresh_token(token: str) -> dict[str, Any]:
    """
    Obtain a new access token using a refresh token.

    Returns the same shape as exchange_code_for_token.
    Raises:
        HEMISAuthError if the refresh token is expired/revoked.
        HEMISUnavailableError if HEMIS cannot be reached.
    """
    payload: dict[str, str] = {
        "grant_type": "refresh_token",
        "refresh_token": token,
        "client_id": settings.HEMIS_CLIENT_ID,
        "client_secret": settings.HEMIS_CLIENT_SECRET,
    }

    try:
        async with httpx.AsyncClient(timeout=TOKEN_TIMEOUT) as client:
            response = await client.post(TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (400, 401):
            raise HEMISAuthError("Refresh token is invalid or expired") from exc
        logger.error("HEMIS refresh failed: {}", exc)
        raise HEMISAuthError(f"Token refresh failed: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.error("HEMIS unreachable during token refresh: {}", exc)
        raise HEMISUnavailableError("HEMIS is unreachable") from exc

    _validate_token_response(data)
    logger.info("HEMIS token refresh successful")
    return _enrich_token(data)


# ─── Revoke ───────────────────────────────────────────────────────────────────

async def revoke_token(token: str) -> None:
    """
    Best-effort token revocation. Silently ignores network errors.
    """
    revoke_url = "https://student.hemis.uz/oauth/revoke"
    try:
        async with httpx.AsyncClient(timeout=TOKEN_TIMEOUT) as client:
            await client.post(
                revoke_url,
                data={
                    "token": token,
                    "client_id": settings.HEMIS_CLIENT_ID,
                    "client_secret": settings.HEMIS_CLIENT_SECRET,
                },
            )
        logger.debug("HEMIS token revoked")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not revoke HEMIS token: {}", exc)


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _validate_token_response(data: dict) -> None:
    for field in ("access_token",):
        if field not in data:
            raise HEMISAuthError(f"Token response missing field: {field!r}")


def _enrich_token(data: dict) -> dict:
    """Add a computed expires_at ISO timestamp for convenience."""
    expires_in = int(data.get("expires_in", 3600))
    data["expires_at"] = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()
    return data


# ─── Exceptions ───────────────────────────────────────────────────────────────

class HEMISAuthError(Exception):
    """Raised when OAuth flow fails (bad code, expired token, etc.)."""


class HEMISUnavailableError(Exception):
    """Raised when HEMIS cannot be reached (network / timeout)."""
