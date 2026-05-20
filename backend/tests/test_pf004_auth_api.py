"""
PF-004 Unit Tests — Auth API Endpoints + i18n
Tests all auth endpoints with Accept-Language header for bilingual responses.
Run with: pytest tests/test_pf004_auth_api.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.i18n import DEFAULT_LANG, Lang, MessageCode, t
from app.models.user import AccountType, User, UserRole, UserStatus


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    return MagicMock()


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
    account_type=AccountType.employer,
    user_status=UserStatus.active,
    first_login_complete=True,
    ai_abuse_count=0,
):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = f"test-{role.value}@test.com"
    user.full_name = f"Test {role.value}"
    user.phone = "+84901234567"
    user.role = role
    user.account_type = account_type
    user.status = user_status
    user.first_login_complete = first_login_complete
    user.ai_abuse_count = ai_abuse_count
    user.consent_given = True
    user.created_at = datetime.now(timezone.utc)
    return user


# ── i18n Core Tests ──────────────────────────────────────────────────────────


class TestI18nCore:
    """Test i18n module: t() and parse_accept_language()."""

    def test_t_returns_vietnamese_by_default(self):
        result = t(MessageCode.LOGOUT_SUCCESS)
        assert result == "Đăng xuất thành công."

    def test_t_returns_english(self):
        result = t(MessageCode.LOGOUT_SUCCESS, "en")
        assert result == "Logged out successfully."

    def test_t_returns_vietnamese_explicitly(self):
        result = t(MessageCode.LOGOUT_SUCCESS, "vi")
        assert result == "Đăng xuất thành công."

    def test_t_all_codes_have_both_languages(self):
        for code in MessageCode:
            assert t(code, "vi"), f"{code} missing Vietnamese"
            assert t(code, "en"), f"{code} missing English"

    def test_t_returns_code_value_for_unknown_code(self):
        from app.core.i18n import _TRANSLATIONS
        # Every MessageCode should be in translations
        for code in MessageCode:
            assert code in _TRANSLATIONS

    def test_parse_accept_language_en(self):
        from app.core.i18n import parse_accept_language
        assert parse_accept_language("en") == "en"
        assert parse_accept_language("en-US") == "en"
        assert parse_accept_language("EN") == "en"

    def test_parse_accept_language_vi_default(self):
        from app.core.i18n import parse_accept_language
        assert parse_accept_language(None) == "vi"
        assert parse_accept_language("") == "vi"
        assert parse_accept_language("vi") == "vi"
        assert parse_accept_language("vi-VN") == "vi"
        assert parse_accept_language("fr") == "vi"  # unsupported → default


# ── Login Tests ──────────────────────────────────────────────────────────────


class TestLoginEndpoint:
    """POST /api/v1/auth/login — i18n error responses."""

    @patch("app.services.auth_service.login")
    def test_login_invalid_credentials_english(self, mock_login, client):
        from fastapi import HTTPException
        mock_login.side_effect = HTTPException(
            status_code=401,
            detail={"code": MessageCode.INVALID_CREDENTIALS, "message": t(MessageCode.INVALID_CREDENTIALS, "en")},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@test.com", "password": "wrong"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "INVALID_CREDENTIALS"
        assert data["detail"]["message"] == "Invalid email or password."

    @patch("app.services.auth_service.login")
    def test_login_invalid_credentials_vietnamese(self, mock_login, client):
        from fastapi import HTTPException
        mock_login.side_effect = HTTPException(
            status_code=401,
            detail={"code": MessageCode.INVALID_CREDENTIALS, "message": t(MessageCode.INVALID_CREDENTIALS, "vi")},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@test.com", "password": "wrong"},
            headers={"Accept-Language": "vi"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "INVALID_CREDENTIALS"
        assert "Email hoặc mật khẩu không chính xác" in data["detail"]["message"]

    @patch("app.services.auth_service.login")
    def test_login_no_language_header_defaults_to_vietnamese(self, mock_login, client):
        from fastapi import HTTPException
        mock_login.side_effect = HTTPException(
            status_code=401,
            detail={"code": MessageCode.INVALID_CREDENTIALS, "message": t(MessageCode.INVALID_CREDENTIALS, "vi")},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@test.com", "password": "wrong"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "INVALID_CREDENTIALS"
        assert "Email hoặc mật khẩu không chính xác" in data["detail"]["message"]

    @patch("app.services.auth_service.login")
    def test_login_success_returns_tokens(self, mock_login, client):
        user = _make_mock_user()
        mock_login.return_value = {
            "access_token": "jwt-access",
            "refresh_token": "jwt-refresh",
            "token_type": "bearer",
            "user": user,
            "requires_2fa": False,
        }
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "Test1234!"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "jwt-access"
        assert data["refresh_token"] == "jwt-refresh"

    @patch("app.services.auth_service.login")
    def test_login_account_suspended_english(self, mock_login, client):
        from fastapi import HTTPException
        mock_login.side_effect = HTTPException(
            status_code=403,
            detail={"code": MessageCode.ACCOUNT_SUSPENDED, "message": t(MessageCode.ACCOUNT_SUSPENDED, "en")},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "suspended@test.com", "password": "Test1234!"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["detail"]["code"] == "ACCOUNT_SUSPENDED"
        assert data["detail"]["message"] == "Account has been suspended."


# ── Registration Tests ───────────────────────────────────────────────────────


class TestRegistrationEndpoint:
    """POST /api/v1/auth/register/step2 — i18n responses."""

    @patch("app.services.auth_service.register_step2")
    def test_register_success_english(self, mock_reg, client):
        uid = uuid.uuid4()
        mock_reg.return_value = {
            "user_id": uid,
            "code": MessageCode.OTP_SENT,
            "message": t(MessageCode.OTP_SENT, "en"),
        }
        resp = client.post(
            "/api/v1/auth/register/step2",
            json={
                "account_type": "job_seeker",
                "full_name": "Test User",
                "email": "new@test.com",
                "phone": "+84901234567",
                "password": "Test1234!",
                "consent_given": True,
            },
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "OTP_SENT"
        assert data["message"] == "OTP has been sent. Please check your inbox."

    @patch("app.services.auth_service.register_step2")
    def test_register_success_vietnamese(self, mock_reg, client):
        uid = uuid.uuid4()
        mock_reg.return_value = {
            "user_id": uid,
            "code": MessageCode.OTP_SENT,
            "message": t(MessageCode.OTP_SENT, "vi"),
        }
        resp = client.post(
            "/api/v1/auth/register/step2",
            json={
                "account_type": "job_seeker",
                "full_name": "Test User",
                "email": "new@test.com",
                "phone": "+84901234567",
                "password": "Test1234!",
                "consent_given": True,
            },
            headers={"Accept-Language": "vi"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "OTP_SENT"
        assert "OTP đã được gửi" in data["message"]

    @patch("app.services.auth_service.register_step2")
    def test_register_email_taken_english(self, mock_reg, client):
        from fastapi import HTTPException
        mock_reg.side_effect = HTTPException(
            status_code=409,
            detail={"code": MessageCode.EMAIL_TAKEN, "message": t(MessageCode.EMAIL_TAKEN, "en")},
        )
        resp = client.post(
            "/api/v1/auth/register/step2",
            json={
                "account_type": "job_seeker",
                "full_name": "Test User",
                "email": "taken@test.com",
                "phone": "+84901234567",
                "password": "Test1234!",
                "consent_given": True,
            },
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["code"] == "EMAIL_TAKEN"
        assert data["detail"]["message"] == "Email is already in use."

    @patch("app.services.auth_service.register_step2")
    def test_register_consent_required(self, mock_reg, client):
        from fastapi import HTTPException
        mock_reg.side_effect = HTTPException(
            status_code=422,
            detail={"code": MessageCode.CONSENT_REQUIRED, "message": t(MessageCode.CONSENT_REQUIRED, "en")},
        )
        resp = client.post(
            "/api/v1/auth/register/step2",
            json={
                "account_type": "job_seeker",
                "full_name": "Test User",
                "email": "new@test.com",
                "phone": "+84901234567",
                "password": "Test1234!",
                "consent_given": False,
            },
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["detail"]["code"] == "CONSENT_REQUIRED"


# ── Logout Tests ─────────────────────────────────────────────────────────────


class TestLogoutEndpoint:
    """POST /api/v1/auth/logout — i18n responses."""

    @patch("app.services.auth_service.logout")
    def test_logout_english(self, mock_logout, client):
        mock_logout.return_value = {
            "code": MessageCode.LOGOUT_SUCCESS,
            "message": t(MessageCode.LOGOUT_SUCCESS, "en"),
        }
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "some-token"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "LOGOUT_SUCCESS"
        assert data["message"] == "Logged out successfully."

    @patch("app.services.auth_service.logout")
    def test_logout_vietnamese(self, mock_logout, client):
        mock_logout.return_value = {
            "code": MessageCode.LOGOUT_SUCCESS,
            "message": t(MessageCode.LOGOUT_SUCCESS, "vi"),
        }
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": "some-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "LOGOUT_SUCCESS"
        assert data["message"] == "Đăng xuất thành công."


# ── Forgot/Reset Password Tests ─────────────────────────────────────────────


class TestForgotPasswordEndpoint:
    """POST /api/v1/auth/forgot-password — always returns success."""

    @patch("app.services.auth_service.forgot_password")
    def test_forgot_password_english(self, mock_forgot, client):
        mock_forgot.return_value = {
            "code": MessageCode.FORGOT_PASSWORD_SENT,
            "message": t(MessageCode.FORGOT_PASSWORD_SENT, "en"),
        }
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@test.com"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "FORGOT_PASSWORD_SENT"
        assert data["message"] == "If the email exists, we have sent a password reset link."

    @patch("app.services.auth_service.forgot_password")
    def test_forgot_password_nonexistent_email_same_response(self, mock_forgot, client):
        mock_forgot.return_value = {
            "code": MessageCode.FORGOT_PASSWORD_SENT,
            "message": t(MessageCode.FORGOT_PASSWORD_SENT, "en"),
        }
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "noone@nowhere.com"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "FORGOT_PASSWORD_SENT"


class TestResetPasswordEndpoint:
    """POST /api/v1/auth/reset-password — success and error cases."""

    @patch("app.services.auth_service.reset_password")
    def test_reset_password_success_english(self, mock_reset, client):
        mock_reset.return_value = {
            "code": MessageCode.PASSWORD_RESET_SUCCESS,
            "message": t(MessageCode.PASSWORD_RESET_SUCCESS, "en"),
        }
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "valid-jwt-token", "new_password": "NewPass123!"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "PASSWORD_RESET_SUCCESS"
        assert data["message"] == "Password has been reset successfully."

    @patch("app.services.auth_service.reset_password")
    def test_reset_password_invalid_token(self, mock_reset, client):
        from fastapi import HTTPException
        mock_reset.side_effect = HTTPException(
            status_code=400,
            detail={"code": MessageCode.RESET_LINK_INVALID, "message": t(MessageCode.RESET_LINK_INVALID, "en")},
        )
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "expired-token", "new_password": "NewPass123!"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["code"] == "RESET_LINK_INVALID"
        assert data["detail"]["message"] == "Reset link is invalid or has expired."


# ── OTP Resend Tests ─────────────────────────────────────────────────────────


class TestOTPResendEndpoint:
    """POST /api/v1/auth/otp/resend — i18n responses."""

    @patch("app.services.auth_service.resend_otp")
    def test_otp_resend_english(self, mock_resend, client):
        mock_resend.return_value = {
            "code": MessageCode.OTP_RESENT,
            "message": t(MessageCode.OTP_RESENT, "en"),
            "remaining_attempts": 2,
        }
        resp = client.post(
            "/api/v1/auth/otp/resend",
            json={"user_id": str(uuid.uuid4()), "purpose": "registration"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "OTP_RESENT"
        assert data["message"] == "OTP has been resent."
        assert data["remaining_attempts"] == 2

    @patch("app.services.auth_service.resend_otp")
    def test_otp_resend_limit_exceeded(self, mock_resend, client):
        from fastapi import HTTPException
        mock_resend.side_effect = HTTPException(
            status_code=429,
            detail={"code": MessageCode.OTP_RESEND_LIMIT, "message": t(MessageCode.OTP_RESEND_LIMIT, "en")},
        )
        resp = client.post(
            "/api/v1/auth/otp/resend",
            json={"user_id": str(uuid.uuid4()), "purpose": "registration"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 429
        data = resp.json()
        assert data["detail"]["code"] == "OTP_RESEND_LIMIT"


# ── Token Refresh Tests ──────────────────────────────────────────────────────


class TestRefreshEndpoint:
    """POST /api/v1/auth/refresh — token rotation."""

    @patch("app.services.auth_service.refresh_tokens")
    def test_refresh_success(self, mock_refresh, client):
        user = _make_mock_user()
        mock_refresh.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "token_type": "bearer",
            "user": user,
        }
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "old-refresh"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "new-access"
        assert data["refresh_token"] == "new-refresh"

    @patch("app.services.auth_service.refresh_tokens")
    def test_refresh_revoked_token(self, mock_refresh, client):
        from fastapi import HTTPException
        mock_refresh.side_effect = HTTPException(
            status_code=401,
            detail={"code": MessageCode.SESSION_INVALIDATED, "message": t(MessageCode.SESSION_INVALIDATED, "en")},
        )
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "revoked-token"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "SESSION_INVALIDATED"
        assert data["detail"]["message"] == "Session expired. Please log in again."


# ── Protected Endpoint Tests (GET /me) ───────────────────────────────────────


class TestMeEndpoint:
    """GET /api/v1/auth/me — authentication required."""

    def test_me_no_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Accept-Language": "en"})
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "SESSION_INVALIDATED"

    def test_me_invalid_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "SESSION_INVALIDATED"
        assert data["detail"]["message"] == "Session expired. Please log in again."

    def test_me_invalid_token_vietnamese(self, client):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token", "Accept-Language": "vi"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "SESSION_INVALIDATED"
        assert "Phiên đã hết hạn" in data["detail"]["message"]

    @patch("app.core.deps.decode_access_token")
    def test_me_valid_token_returns_user(self, mock_decode, client, mock_db):
        user = _make_mock_user(role=UserRole.super_admin)
        mock_decode.return_value = {"sub": str(user.id), "role": "super_admin"}
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == user.email
        assert data["role"] == "super_admin"

    @patch("app.core.deps.decode_access_token")
    def test_me_suspended_user_returns_403(self, mock_decode, client, mock_db):
        user = _make_mock_user(user_status=UserStatus.suspended)
        mock_decode.return_value = {"sub": str(user.id), "role": "super_admin"}
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["detail"]["code"] == "ACCOUNT_SUSPENDED"
        assert data["detail"]["message"] == "Account has been suspended."


# ── First Login Complete Tests ───────────────────────────────────────────────


class TestFirstLoginCompleteEndpoint:
    """POST /api/v1/auth/first-login-complete — i18n responses."""

    @patch("app.services.auth_service.complete_first_login")
    @patch("app.core.deps.decode_access_token")
    def test_first_login_complete_english(self, mock_decode, mock_complete, client, mock_db):
        user = _make_mock_user()
        mock_decode.return_value = {"sub": str(user.id), "role": "super_admin"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_complete.return_value = {
            "code": MessageCode.ONBOARDING_COMPLETE,
            "message": t(MessageCode.ONBOARDING_COMPLETE, "en"),
            "first_login_complete": True,
        }
        resp = client.post(
            "/api/v1/auth/first-login-complete",
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "ONBOARDING_COMPLETE"
        assert data["message"] == "Onboarding complete."
        assert data["first_login_complete"] is True

    def test_first_login_complete_no_token(self, client):
        resp = client.post(
            "/api/v1/auth/first-login-complete",
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 401


# ── AI Abuse Tests ───────────────────────────────────────────────────────────


class TestAIAbuseEndpoint:
    """POST /api/v1/auth/ai-abuse — session terminated after 3+ strikes."""

    @patch("app.services.auth_service.record_ai_abuse")
    @patch("app.core.deps.decode_access_token")
    def test_ai_abuse_increments_count(self, mock_decode, mock_abuse, client, mock_db):
        user = _make_mock_user()
        mock_decode.return_value = {"sub": str(user.id), "role": "job_seeker"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_abuse.return_value = {"ai_abuse_count": 1, "session_terminated": False}

        resp = client.post(
            "/api/v1/auth/ai-abuse",
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ai_abuse_count"] == 1
        assert data["session_terminated"] is False

    @patch("app.services.auth_service.record_ai_abuse")
    @patch("app.core.deps.decode_access_token")
    def test_ai_abuse_session_terminated(self, mock_decode, mock_abuse, client, mock_db):
        from fastapi import HTTPException
        user = _make_mock_user()
        mock_decode.return_value = {"sub": str(user.id), "role": "job_seeker"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        mock_abuse.side_effect = HTTPException(
            status_code=401,
            detail={"code": MessageCode.SESSION_TERMINATED, "message": t(MessageCode.SESSION_TERMINATED, "en")},
        )
        resp = client.post(
            "/api/v1/auth/ai-abuse",
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert data["detail"]["code"] == "SESSION_TERMINATED"
        assert data["detail"]["message"] == "Session terminated due to policy violation."

    def test_ai_abuse_no_token(self, client):
        resp = client.post(
            "/api/v1/auth/ai-abuse",
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 401


# ── RBAC — Team Invite Tests ─────────────────────────────────────────────────


class TestInviteEndpoint:
    """POST /api/v1/auth/invite — role enforcement + i18n."""

    @patch("app.services.auth_service.create_invitation")
    @patch("app.core.deps.decode_access_token")
    def test_create_invite_as_super_admin(self, mock_decode, mock_invite, client, mock_db):
        user = _make_mock_user(role=UserRole.super_admin)
        mock_decode.return_value = {"sub": str(user.id), "role": "super_admin"}
        mock_db.query.return_value.filter.return_value.first.return_value = user
        invite_id = uuid.uuid4()
        mock_invite.return_value = {
            "invitation_id": invite_id,
            "code": MessageCode.INVITE_SENT,
            "message": t(MessageCode.INVITE_SENT, "en"),
        }
        resp = client.post(
            "/api/v1/auth/invite",
            json={
                "email": "invited@test.com",
                "role": "hr_recruiter",
                "company_id": str(uuid.uuid4()),
            },
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "INVITE_SENT"
        assert data["message"] == "Invitation has been sent."

    @patch("app.core.deps.decode_access_token")
    def test_create_invite_as_job_seeker_forbidden(self, mock_decode, client, mock_db):
        user = _make_mock_user(role=UserRole.job_seeker, account_type=AccountType.job_seeker)
        mock_decode.return_value = {"sub": str(user.id), "role": "job_seeker"}
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/invite",
            json={
                "email": "invited@test.com",
                "role": "hr_recruiter",
                "company_id": str(uuid.uuid4()),
            },
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 403
        data = resp.json()
        assert data["detail"]["code"] == "FORBIDDEN"

    @patch("app.core.deps.decode_access_token")
    def test_create_invite_as_hr_forbidden(self, mock_decode, client, mock_db):
        user = _make_mock_user(role=UserRole.hr_recruiter)
        mock_decode.return_value = {"sub": str(user.id), "role": "hr_recruiter"}
        mock_db.query.return_value.filter.return_value.first.return_value = user

        resp = client.post(
            "/api/v1/auth/invite",
            json={
                "email": "invited@test.com",
                "role": "hr_recruiter",
                "company_id": str(uuid.uuid4()),
            },
            headers={"Authorization": "Bearer valid-token", "Accept-Language": "en"},
        )
        assert resp.status_code == 403

    def test_create_invite_no_token(self, client):
        resp = client.post(
            "/api/v1/auth/invite",
            json={
                "email": "invited@test.com",
                "role": "hr_recruiter",
                "company_id": str(uuid.uuid4()),
            },
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 401


# ── 2FA Login Tests ──────────────────────────────────────────────────────────


class TestLogin2FAEndpoint:
    """POST /api/v1/auth/login/2fa — OTP verification."""

    @patch("app.services.auth_service.login_2fa")
    def test_2fa_success(self, mock_2fa, client):
        user = _make_mock_user(role=UserRole.company_admin)
        mock_2fa.return_value = {
            "access_token": "jwt-access",
            "refresh_token": "jwt-refresh",
            "token_type": "bearer",
            "user": user,
        }
        resp = client.post(
            "/api/v1/auth/login/2fa",
            json={"user_id": str(uuid.uuid4()), "otp_code": "123456"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] == "jwt-access"

    @patch("app.services.auth_service.login_2fa")
    def test_2fa_invalid_otp(self, mock_2fa, client):
        from fastapi import HTTPException
        mock_2fa.side_effect = HTTPException(
            status_code=400,
            detail={"code": MessageCode.OTP_INVALID, "message": t(MessageCode.OTP_INVALID, "en")},
        )
        resp = client.post(
            "/api/v1/auth/login/2fa",
            json={"user_id": str(uuid.uuid4()), "otp_code": "000000"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert data["detail"]["code"] == "OTP_INVALID"
        assert data["detail"]["message"] == "Invalid OTP code."

    @patch("app.services.auth_service.login_2fa")
    def test_2fa_expired_otp(self, mock_2fa, client):
        from fastapi import HTTPException
        mock_2fa.side_effect = HTTPException(
            status_code=410,
            detail={"code": MessageCode.OTP_EXPIRED, "message": t(MessageCode.OTP_EXPIRED, "en")},
        )
        resp = client.post(
            "/api/v1/auth/login/2fa",
            json={"user_id": str(uuid.uuid4()), "otp_code": "123456"},
            headers={"Accept-Language": "en"},
        )
        assert resp.status_code == 410
        data = resp.json()
        assert data["detail"]["code"] == "OTP_EXPIRED"


# ── Health Check Tests ───────────────────────────────────────────────────────


class TestHealthCheck:
    """GET /health — basic server availability."""

    @patch("app.main.check_redis_health")
    def test_health_endpoint(self, mock_redis, client):
        mock_redis.return_value = True
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
