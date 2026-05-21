"""
JWT encode/decode + password hashing utilities.
PRD: AUTH-FR-006 (JWT sessions), AUTH-FR-002 (password auth)
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt as pyjwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.config import get_settings

settings = get_settings()


# ── Custom exceptions ────────────────────────────────────────────────

class TokenExpiredException(Exception):
    """Raised when a JWT token has expired."""
    pass


class InvalidTokenException(Exception):
    """Raised when a JWT token is tampered, malformed, or otherwise invalid."""
    pass

# ── Password hashing ──────────────────────────────────────────────────

_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ── JWT tokens ─────────────────────────────────────────────────────────

def create_access_token(user_id: UUID, role: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRY_MINUTES),
    }
    if extra:
        payload.update(extra)
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> tuple[str, str, datetime]:
    """Return (raw_token, token_hash, expires_at)."""
    raw = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_DAYS)
    return raw, token_hash, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode an access JWT. Raises TokenExpiredException or InvalidTokenException."""
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise InvalidTokenException("Token type is not 'access'")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredException("Access token has expired")
    except InvalidTokenError:
        raise InvalidTokenException("Access token is invalid or tampered")


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Password-reset / Invite JWT ───────────────────────────────────────

def create_reset_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "password_reset",
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_reset_token(token: str) -> dict[str, Any]:
    """Decode a password-reset JWT. Raises TokenExpiredException or InvalidTokenException."""
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "password_reset":
            raise InvalidTokenException("Token type is not 'password_reset'")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredException("Reset token has expired")
    except InvalidTokenError:
        raise InvalidTokenException("Reset token is invalid or tampered")


def create_invite_token(invitation_id: UUID, email: str) -> tuple[str, str]:
    """Return (jwt_token, token_hash) for team invite."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(invitation_id),
        "email": email,
        "type": "team_invite",
        "iat": now,
        "exp": now + timedelta(hours=settings.INVITE_TTL_HOURS),
    }
    raw = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def decode_invite_token(token: str) -> dict[str, Any]:
    """Decode a team-invite JWT. Raises TokenExpiredException or InvalidTokenException."""
    try:
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "team_invite":
            raise InvalidTokenException("Token type is not 'team_invite'")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredException("Invite token has expired")
    except InvalidTokenError:
        raise InvalidTokenException("Invite token is invalid or tampered")
