"""
US-002 Unit Tests — F2.2 Security Utilities
Validates all acceptance criteria for core/security.py:
  AC1: create_access_token returns signed JWT with correct claims and expiry
  AC2: decode functions raise TokenExpiredException / InvalidTokenException distinctly
  AC3: hash_password uses argon2 with unique salt each call
  AC4: verify_password returns True only for correct password
  AC5: JWT_EXPIRY_MINUTES and JWT_REFRESH_DAYS control token lifetimes

Run with: pytest tests/test_us002_security.py -v
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt as pyjwt
import pytest

from app.config import get_settings
from app.core.security import (
    InvalidTokenException,
    TokenExpiredException,
    create_access_token,
    create_invite_token,
    create_refresh_token,
    create_reset_token,
    decode_access_token,
    decode_invite_token,
    decode_reset_token,
    hash_password,
    hash_token,
    verify_password,
)

settings = get_settings()

# ── Test Data ──────────────────────────────────────────────────────────────────

TEST_USER_ID = uuid.uuid4()
TEST_INVITE_ID = uuid.uuid4()
TEST_ROLE = "super_admin"
TEST_PASSWORD = "SecurePass123!"
TEST_WRONG_PASSWORD = "WrongPass456!"


# ── AC1: create_access_token ──────────────────────────────────────────────────


class TestAC1CreateAccessToken:
    """AC1: create_access_token(user_id, role) returns signed JWT with correct claims and expiry."""

    def test_returns_string(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_sub_claim(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == str(TEST_USER_ID)

    def test_contains_role_claim(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["role"] == TEST_ROLE

    def test_contains_type_access(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "access"

    def test_contains_iat_claim(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert "iat" in payload
        assert isinstance(payload["iat"], (int, float))

    def test_contains_exp_claim(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_expiry_matches_config(self):
        """exp should be ~JWT_EXPIRY_MINUTES from now."""
        before = datetime.now(timezone.utc)
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        after = datetime.now(timezone.utc)

        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        # PyJWT truncates to integer seconds, so allow 2s tolerance
        expected_min = before + timedelta(minutes=settings.JWT_EXPIRY_MINUTES) - timedelta(seconds=2)
        expected_max = after + timedelta(minutes=settings.JWT_EXPIRY_MINUTES) + timedelta(seconds=2)

        assert expected_min <= exp <= expected_max

    def test_extra_claims_included(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE, extra={"custom": "value"})
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["custom"] == "value"

    def test_different_roles(self):
        """Token created with different roles should have correct role claim."""
        for role in ["super_admin", "company_admin", "hr_recruiter", "job_seeker"]:
            token = create_access_token(TEST_USER_ID, role)
            payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            assert payload["role"] == role

    def test_different_users_get_different_tokens(self):
        t1 = create_access_token(uuid.uuid4(), TEST_ROLE)
        t2 = create_access_token(uuid.uuid4(), TEST_ROLE)
        assert t1 != t2


# ── AC1: create_refresh_token ─────────────────────────────────────────────────


class TestCreateRefreshToken:
    """create_refresh_token returns (raw, hash, expires_at)."""

    def test_returns_tuple_of_three(self):
        raw, token_hash, expires_at = create_refresh_token(TEST_USER_ID)
        assert isinstance(raw, str)
        assert isinstance(token_hash, str)
        assert isinstance(expires_at, datetime)

    def test_raw_token_is_url_safe(self):
        raw, _, _ = create_refresh_token(TEST_USER_ID)
        assert len(raw) > 40  # secrets.token_urlsafe(64) → ~86 chars

    def test_hash_is_sha256_hex(self):
        _, token_hash, _ = create_refresh_token(TEST_USER_ID)
        assert len(token_hash) == 64  # SHA-256 hex digest

    def test_expires_at_matches_config(self):
        before = datetime.now(timezone.utc)
        _, _, expires_at = create_refresh_token(TEST_USER_ID)
        after = datetime.now(timezone.utc)

        expected_min = before + timedelta(days=settings.JWT_REFRESH_DAYS)
        expected_max = after + timedelta(days=settings.JWT_REFRESH_DAYS)

        assert expected_min <= expires_at <= expected_max

    def test_unique_tokens_each_call(self):
        r1, h1, _ = create_refresh_token(TEST_USER_ID)
        r2, h2, _ = create_refresh_token(TEST_USER_ID)
        assert r1 != r2
        assert h1 != h2

    def test_hash_matches_raw(self):
        raw, token_hash, _ = create_refresh_token(TEST_USER_ID)
        assert hash_token(raw) == token_hash


# ── AC2: decode — expired vs tampered ─────────────────────────────────────────


class TestAC2DecodeAccessToken:
    """AC2: decode_access_token raises TokenExpiredException for expired, InvalidTokenException for tampered."""

    def test_valid_token_returns_payload(self):
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = decode_access_token(token)
        assert payload["sub"] == str(TEST_USER_ID)
        assert payload["role"] == TEST_ROLE
        assert payload["type"] == "access"

    def test_expired_token_raises_token_expired(self):
        """Create a token that's already expired, then decode it."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(TEST_USER_ID),
            "role": TEST_ROLE,
            "type": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(seconds=1),
        }
        token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(TokenExpiredException):
            decode_access_token(token)

    def test_tampered_token_raises_invalid_token(self):
        """Modify a token's signature to simulate tampering."""
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(InvalidTokenException):
            decode_access_token(tampered)

    def test_wrong_secret_raises_invalid_token(self):
        """Token signed with different secret."""
        payload = {
            "sub": str(TEST_USER_ID),
            "role": TEST_ROLE,
            "type": "access",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        }
        token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(InvalidTokenException):
            decode_access_token(token)

    def test_wrong_type_raises_invalid_token(self):
        """Token with type != 'access' should raise InvalidTokenException."""
        payload = {
            "sub": str(TEST_USER_ID),
            "role": TEST_ROLE,
            "type": "password_reset",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        }
        token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(InvalidTokenException):
            decode_access_token(token)

    def test_garbage_string_raises_invalid_token(self):
        with pytest.raises(InvalidTokenException):
            decode_access_token("not-a-jwt-at-all")

    def test_empty_string_raises_invalid_token(self):
        with pytest.raises(InvalidTokenException):
            decode_access_token("")


class TestAC2DecodeResetToken:
    """AC2: decode_reset_token raises distinct exceptions."""

    def test_valid_reset_token(self):
        token = create_reset_token(TEST_USER_ID)
        payload = decode_reset_token(token)
        assert payload["sub"] == str(TEST_USER_ID)
        assert payload["type"] == "password_reset"

    def test_expired_reset_token_raises_token_expired(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(TEST_USER_ID),
            "type": "password_reset",
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(seconds=1),
        }
        token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(TokenExpiredException):
            decode_reset_token(token)

    def test_tampered_reset_token_raises_invalid(self):
        token = create_reset_token(TEST_USER_ID)
        tampered = token[:-5] + "ZZZZZ"

        with pytest.raises(InvalidTokenException):
            decode_reset_token(tampered)

    def test_wrong_type_raises_invalid(self):
        """An access token passed to decode_reset_token should raise InvalidTokenException."""
        token = create_access_token(TEST_USER_ID, TEST_ROLE)

        with pytest.raises(InvalidTokenException):
            decode_reset_token(token)


class TestAC2DecodeInviteToken:
    """AC2: decode_invite_token raises distinct exceptions."""

    def test_valid_invite_token(self):
        token, _ = create_invite_token(TEST_INVITE_ID, "invite@test.com")
        payload = decode_invite_token(token)
        assert payload["sub"] == str(TEST_INVITE_ID)
        assert payload["email"] == "invite@test.com"
        assert payload["type"] == "team_invite"

    def test_expired_invite_token_raises_token_expired(self):
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(TEST_INVITE_ID),
            "email": "test@test.com",
            "type": "team_invite",
            "iat": now - timedelta(days=4),
            "exp": now - timedelta(seconds=1),
        }
        token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(TokenExpiredException):
            decode_invite_token(token)

    def test_tampered_invite_token_raises_invalid(self):
        token, _ = create_invite_token(TEST_INVITE_ID, "invite@test.com")
        tampered = token[:-5] + "AAAAA"

        with pytest.raises(InvalidTokenException):
            decode_invite_token(tampered)

    def test_wrong_type_raises_invalid(self):
        """A reset token passed to decode_invite_token should raise InvalidTokenException."""
        token = create_reset_token(TEST_USER_ID)

        with pytest.raises(InvalidTokenException):
            decode_invite_token(token)


# ── AC3: hash_password uses argon2 with unique salt ───────────────────────────


class TestAC3HashPassword:
    """AC3: hash_password uses argon2 with unique salt each call."""

    def test_returns_string(self):
        hashed = hash_password(TEST_PASSWORD)
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_starts_with_argon2_prefix(self):
        """argon2 hashes start with $argon2id$ or $argon2i$."""
        hashed = hash_password(TEST_PASSWORD)
        assert hashed.startswith("$argon2")

    def test_unique_salt_per_call(self):
        """Two calls with same password must produce different hashes (different salt)."""
        h1 = hash_password(TEST_PASSWORD)
        h2 = hash_password(TEST_PASSWORD)
        assert h1 != h2

    def test_hash_is_not_plaintext(self):
        hashed = hash_password(TEST_PASSWORD)
        assert TEST_PASSWORD not in hashed

    def test_different_passwords_different_hashes(self):
        h1 = hash_password("Password1!")
        h2 = hash_password("Password2!")
        assert h1 != h2


# ── AC4: verify_password ──────────────────────────────────────────────────────


class TestAC4VerifyPassword:
    """AC4: verify_password(plain, hash) returns True only for correct password."""

    def test_correct_password_returns_true(self):
        hashed = hash_password(TEST_PASSWORD)
        assert verify_password(TEST_PASSWORD, hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password(TEST_PASSWORD)
        assert verify_password(TEST_WRONG_PASSWORD, hashed) is False

    def test_empty_password_returns_false(self):
        hashed = hash_password(TEST_PASSWORD)
        assert verify_password("", hashed) is False

    def test_invalid_hash_returns_false(self):
        assert verify_password(TEST_PASSWORD, "not-a-valid-hash") is False

    def test_empty_hash_returns_false(self):
        assert verify_password(TEST_PASSWORD, "") is False

    def test_case_sensitive(self):
        hashed = hash_password("Password123!")
        assert verify_password("password123!", hashed) is False

    def test_unicode_password(self):
        pwd = "Mậtkhẩu123!"
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_long_password(self):
        pwd = "A" * 200
        hashed = hash_password(pwd)
        assert verify_password(pwd, hashed) is True

    def test_verify_returns_bool(self):
        hashed = hash_password(TEST_PASSWORD)
        result = verify_password(TEST_PASSWORD, hashed)
        assert isinstance(result, bool)


# ── AC5: JWT env vars control lifetimes ───────────────────────────────────────


class TestAC5EnvVarConfig:
    """AC5: JWT_EXPIRY_MINUTES and JWT_REFRESH_DAYS env vars control token lifetimes."""

    def test_jwt_expiry_minutes_has_default(self):
        assert hasattr(settings, "JWT_EXPIRY_MINUTES")
        assert isinstance(settings.JWT_EXPIRY_MINUTES, int)
        assert settings.JWT_EXPIRY_MINUTES > 0

    def test_jwt_refresh_days_has_default(self):
        assert hasattr(settings, "JWT_REFRESH_DAYS")
        assert isinstance(settings.JWT_REFRESH_DAYS, int)
        assert settings.JWT_REFRESH_DAYS > 0

    def test_jwt_secret_exists(self):
        assert hasattr(settings, "JWT_SECRET")
        assert len(settings.JWT_SECRET) > 0

    def test_jwt_algorithm_exists(self):
        assert settings.JWT_ALGORITHM == "HS256"

    def test_access_token_uses_expiry_minutes(self):
        """Token exp claim should reflect JWT_EXPIRY_MINUTES."""
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        iat = payload["iat"]
        exp = payload["exp"]
        delta_minutes = (exp - iat) / 60
        assert abs(delta_minutes - settings.JWT_EXPIRY_MINUTES) < 1  # within 1 minute tolerance

    def test_refresh_token_uses_refresh_days(self):
        """Refresh token expires_at should reflect JWT_REFRESH_DAYS."""
        before = datetime.now(timezone.utc)
        _, _, expires_at = create_refresh_token(TEST_USER_ID)
        expected = before + timedelta(days=settings.JWT_REFRESH_DAYS)
        diff = abs((expires_at - expected).total_seconds())
        assert diff < 5  # within 5 seconds


# ── Custom Exceptions ─────────────────────────────────────────────────────────


class TestCustomExceptions:
    """Verify custom exception classes exist and are properly typed."""

    def test_token_expired_is_exception(self):
        assert issubclass(TokenExpiredException, Exception)

    def test_invalid_token_is_exception(self):
        assert issubclass(InvalidTokenException, Exception)

    def test_token_expired_not_invalid_token(self):
        """They must be distinct exception types."""
        assert not issubclass(TokenExpiredException, InvalidTokenException)
        assert not issubclass(InvalidTokenException, TokenExpiredException)

    def test_token_expired_has_message(self):
        exc = TokenExpiredException("test expired")
        assert str(exc) == "test expired"

    def test_invalid_token_has_message(self):
        exc = InvalidTokenException("test invalid")
        assert str(exc) == "test invalid"


# ── Centralised Usage ─────────────────────────────────────────────────────────


class TestCentralisedUsage:
    """Verify security functions are used consistently across all auth modules."""

    def test_auth_service_imports_security(self):
        from app.services import auth_service
        assert hasattr(auth_service, "create_access_token")
        assert hasattr(auth_service, "create_refresh_token")
        assert hasattr(auth_service, "hash_password")
        assert hasattr(auth_service, "verify_password")
        assert hasattr(auth_service, "TokenExpiredException")
        assert hasattr(auth_service, "InvalidTokenException")

    def test_deps_imports_decode(self):
        from app.core import deps
        assert hasattr(deps, "decode_access_token")
        assert hasattr(deps, "TokenExpiredException")
        assert hasattr(deps, "InvalidTokenException")

    def test_hash_token_is_sha256(self):
        raw = "test-raw-token"
        hashed = hash_token(raw)
        import hashlib
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert hashed == expected


# ── Reset & Invite Token Creation ─────────────────────────────────────────────


class TestResetAndInviteTokens:
    """Supplementary: create_reset_token, create_invite_token."""

    def test_reset_token_type(self):
        token = create_reset_token(TEST_USER_ID)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "password_reset"
        assert payload["sub"] == str(TEST_USER_ID)

    def test_reset_token_30min_expiry(self):
        token = create_reset_token(TEST_USER_ID)
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        delta_minutes = (payload["exp"] - payload["iat"]) / 60
        assert abs(delta_minutes - 30) < 1

    def test_invite_token_returns_tuple(self):
        token, token_hash = create_invite_token(TEST_INVITE_ID, "test@test.com")
        assert isinstance(token, str)
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64  # SHA-256

    def test_invite_token_type(self):
        token, _ = create_invite_token(TEST_INVITE_ID, "test@test.com")
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "team_invite"
        assert payload["email"] == "test@test.com"

    def test_invite_token_72h_expiry(self):
        token, _ = create_invite_token(TEST_INVITE_ID, "test@test.com")
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        delta_hours = (payload["exp"] - payload["iat"]) / 3600
        assert abs(delta_hours - settings.INVITE_TTL_HOURS) < 1

    def test_invite_hash_matches(self):
        token, token_hash = create_invite_token(TEST_INVITE_ID, "test@test.com")
        assert hash_token(token) == token_hash
