"""
US-005 Unit Tests — F2.5 Account Lockout
Validates all acceptance criteria:
  AC1: 3 consecutive wrong passwords → account locked, HTTP 423 on 4th
  AC2: 2 failures + 1 success → counter reset, NOT locked
  AC3: Locked account visible with status=locked (model-level)
  AC4: Account unlocked only via password reset (Super Admin)
  AC5: Lock event logged to audit log with timestamp (BR-015)

Run with: pytest tests/test_us005_account_lockout.py -v
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.i18n import MessageCode, t
from app.models.audit import AuditLog
from app.models.user import AccountType, User, UserRole, UserStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture
def client(mock_db):
    from app.database import get_db
    from app.main import app

    def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db

    with patch("app.main.wait_for_db"), \
         patch("app.main.Base"), \
         patch("app.main.seed_hello_world"), \
         TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _make_mock_user(
    role=UserRole.super_admin,
    user_status=UserStatus.active,
    failed_login_count=0,
    password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakesalt$fakehash",
):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "locktest@test.com"
    user.full_name = "Lock Test User"
    user.phone = "+84901234567"
    user.role = role
    user.account_type = AccountType.employer
    user.status = user_status
    user.first_login_complete = True
    user.password_hash = password_hash
    user.failed_login_count = failed_login_count
    user.ai_abuse_count = 0
    user.consent_given = True
    user.created_at = datetime.now(timezone.utc)
    user.last_login = None
    return user


# ── AC1: 3 wrong passwords → locked, HTTP 423 on 4th ─────────────────────────


class TestAC1LockAfterThreeFailures:
    """AC1: 3 consecutive wrong passwords → account locked (status=locked), HTTP 423 on 4th attempt."""

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_first_failure_increments_counter(self, mock_verify, client, mock_db):
        user = _make_mock_user(failed_login_count=0)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "wrong"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 401
        assert user.failed_login_count == 1
        assert user.status == UserStatus.active  # not locked yet

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_second_failure_increments_counter(self, mock_verify, client, mock_db):
        user = _make_mock_user(failed_login_count=1)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "wrong"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 401
        assert user.failed_login_count == 2
        assert user.status == UserStatus.active  # not locked yet

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_third_failure_locks_account(self, mock_verify, client, mock_db):
        user = _make_mock_user(failed_login_count=2)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "wrong"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 401
        assert user.failed_login_count == 3
        assert user.status == UserStatus.locked

    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_locked_account_returns_423(self, mock_verify, client, mock_db):
        user = _make_mock_user(user_status=UserStatus.locked, failed_login_count=3)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "correct"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 423
        data = resp.json()
        assert data["detail"]["code"] == "ACCOUNT_LOCKED"

    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_locked_account_returns_423_vietnamese(self, mock_verify, client, mock_db):
        user = _make_mock_user(user_status=UserStatus.locked, failed_login_count=3)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "correct"},
            headers={"Accept-Language": "vi"},
        )

        assert resp.status_code == 423
        data = resp.json()
        assert "khóa" in data["detail"]["message"]

    def test_locked_status_blocks_even_correct_password(self, client, mock_db):
        """AC1 confirming: locked account cannot login even with correct password."""
        user = _make_mock_user(user_status=UserStatus.locked, failed_login_count=3)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "Test1234!"},
            headers={"Accept-Language": "en"},
        )

        # The locked check happens BEFORE password verification
        assert resp.status_code == 423


# ── AC2: 2 failures + 1 success → counter reset ──────────────────────────────


class TestAC2CounterResetOnSuccess:
    """AC2: 2 failures then 1 success → failed_login_count reset, account NOT locked."""

    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_successful_login_resets_counter(self, mock_verify, client, mock_db):
        user = _make_mock_user(failed_login_count=2)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        with patch("app.services.auth_service._issue_tokens") as mock_tokens:
            mock_tokens.return_value = {
                "access_token": "fake.access.token",
                "refresh_token": "fake-refresh",
                "token_type": "bearer",
                "user": user,
            }
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "locktest@test.com", "password": "correct"},
                headers={"Accept-Language": "en"},
            )

        assert resp.status_code == 200
        assert user.failed_login_count == 0
        assert user.status == UserStatus.active

    @patch("app.services.auth_service.verify_password", return_value=True)
    def test_counter_zero_stays_zero_on_success(self, mock_verify, client, mock_db):
        user = _make_mock_user(failed_login_count=0)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        with patch("app.services.auth_service._issue_tokens") as mock_tokens:
            mock_tokens.return_value = {
                "access_token": "fake.access.token",
                "refresh_token": "fake-refresh",
                "token_type": "bearer",
                "user": user,
            }
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "locktest@test.com", "password": "correct"},
                headers={"Accept-Language": "en"},
            )

        assert resp.status_code == 200
        assert user.failed_login_count == 0


# ── AC3: Locked account visible with status=locked ────────────────────────────


class TestAC3LockedStatus:
    """AC3: Locked account visible in User Management with status=locked filter."""

    def test_user_status_enum_has_locked(self):
        assert hasattr(UserStatus, "locked")
        assert UserStatus.locked.value == "locked"

    def test_locked_user_has_correct_status(self):
        user = _make_mock_user(user_status=UserStatus.locked)
        assert user.status == UserStatus.locked

    def test_user_status_enum_values(self):
        """All expected statuses exist."""
        expected = {"pending", "active", "suspended", "locked"}
        actual = {s.value for s in UserStatus}
        assert expected == actual


# ── AC4: Unlock only via password reset ───────────────────────────────────────


class TestAC4UnlockViaPasswordReset:
    """AC4: Account unlocked only when Super Admin issues password reset."""

    @patch("app.services.auth_service.decode_reset_token")
    @patch("app.services.auth_service.hash_password", return_value="$argon2id$newhash")
    def test_password_reset_unlocks_locked_account(self, mock_hash, mock_decode, client, mock_db):
        user = _make_mock_user(user_status=UserStatus.locked, failed_login_count=3)
        mock_decode.return_value = {"sub": str(user.id), "type": "password_reset"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.query.return_value.filter.return_value.update.return_value = 0

        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "valid-reset-token", "new_password": "NewPass123!"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 200
        assert user.status == UserStatus.active
        assert user.failed_login_count == 0

    @patch("app.services.auth_service.decode_reset_token")
    @patch("app.services.auth_service.hash_password", return_value="$argon2id$newhash")
    def test_password_reset_creates_audit_log_for_unlock(self, mock_hash, mock_decode, client, mock_db):
        user = _make_mock_user(user_status=UserStatus.locked, failed_login_count=3)
        mock_decode.return_value = {"sub": str(user.id), "type": "password_reset"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.query.return_value.filter.return_value.update.return_value = 0

        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "valid-reset-token", "new_password": "NewPass123!"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 200
        # Verify AuditLog was added
        add_calls = mock_db.add.call_args_list
        audit_added = any(
            isinstance(c[0][0], AuditLog) and c[0][0].action == "ACCOUNT_UNLOCKED"
            for c in add_calls
            if c[0]
        )
        assert audit_added, "AuditLog with action=ACCOUNT_UNLOCKED should be added"

    @patch("app.services.auth_service.decode_reset_token")
    @patch("app.services.auth_service.hash_password", return_value="$argon2id$newhash")
    def test_password_reset_on_active_account_no_unlock_log(self, mock_hash, mock_decode, client, mock_db):
        """Password reset for a non-locked account should NOT log ACCOUNT_UNLOCKED."""
        user = _make_mock_user(user_status=UserStatus.active, failed_login_count=0)
        mock_decode.return_value = {"sub": str(user.id), "type": "password_reset"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_db.query.return_value.filter.return_value.update.return_value = 0

        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "valid-reset-token", "new_password": "NewPass123!"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 200
        # No ACCOUNT_UNLOCKED audit log for non-locked accounts
        add_calls = mock_db.add.call_args_list
        unlock_logged = any(
            isinstance(c[0][0], AuditLog) and c[0][0].action == "ACCOUNT_UNLOCKED"
            for c in add_calls
            if c[0]
        )
        assert not unlock_logged


# ── AC5: Lock event logged to audit log ───────────────────────────────────────


class TestAC5AuditLog:
    """AC5: Lock event logged to audit log with timestamp (BR-015)."""

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_lock_creates_audit_log(self, mock_verify, client, mock_db):
        user = _make_mock_user(failed_login_count=2)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "wrong"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 401
        assert user.status == UserStatus.locked

        # Verify AuditLog was added with correct fields
        add_calls = mock_db.add.call_args_list
        audit_entries = [
            c[0][0] for c in add_calls if c[0] and isinstance(c[0][0], AuditLog)
        ]
        assert len(audit_entries) == 1
        entry = audit_entries[0]
        assert entry.action == "ACCOUNT_LOCKED"
        assert entry.user_id == user.id
        assert "3" in entry.detail  # mentions the threshold

    @patch("app.services.auth_service.verify_password", return_value=False)
    def test_no_audit_log_before_threshold(self, mock_verify, client, mock_db):
        """No audit log should be created for failures below 3."""
        user = _make_mock_user(failed_login_count=0)
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "locktest@test.com", "password": "wrong"},
            headers={"Accept-Language": "en"},
        )

        assert resp.status_code == 401
        assert user.failed_login_count == 1

        # No audit log for first failure
        add_calls = mock_db.add.call_args_list
        audit_entries = [
            c[0][0] for c in add_calls if c[0] and isinstance(c[0][0], AuditLog)
        ]
        assert len(audit_entries) == 0

    def test_audit_log_model_has_required_fields(self):
        """AuditLog model should have user_id, action, detail, created_at."""
        log = AuditLog(
            user_id=uuid.uuid4(),
            action="ACCOUNT_LOCKED",
            detail="test detail",
            ip_address="127.0.0.1",
        )
        assert log.user_id is not None
        assert log.action == "ACCOUNT_LOCKED"
        assert log.detail == "test detail"
        assert log.ip_address == "127.0.0.1"

    def test_audit_log_model_exists_in_models_package(self):
        from app.models import AuditLog as AL
        assert AL is AuditLog


# ── Constants ─────────────────────────────────────────────────────────────────


class TestConstants:
    """Verify lockout threshold constant."""

    def test_max_attempts_is_3(self):
        from app.services.auth_service import MAX_FAILED_LOGIN_ATTEMPTS
        assert MAX_FAILED_LOGIN_ATTEMPTS == 3


# ── i18n for ACCOUNT_LOCKED ──────────────────────────────────────────────────


class TestAccountLockedI18n:
    """Verify ACCOUNT_LOCKED message code and translations."""

    def test_message_code_exists(self):
        assert hasattr(MessageCode, "ACCOUNT_LOCKED")
        assert MessageCode.ACCOUNT_LOCKED.value == "ACCOUNT_LOCKED"

    def test_english_translation(self):
        msg = t(MessageCode.ACCOUNT_LOCKED, "en")
        assert "locked" in msg.lower()
        assert "failed login" in msg.lower()

    def test_vietnamese_translation(self):
        msg = t(MessageCode.ACCOUNT_LOCKED, "vi")
        assert "khóa" in msg
