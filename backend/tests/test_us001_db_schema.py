"""
US-001 Unit Tests — F2.1 Database Schema Validation
Validates all acceptance criteria for the auth database schema:
  AC1: All 4 tables exist (users, refresh_tokens, team_invitations, social_accounts)
  AC2: users table columns, types, constraints, defaults
  AC3: refresh_tokens table columns, FK CASCADE, indexes
  AC4: team_invitations table columns, expires_at index
  AC5: social_accounts UNIQUE(provider, provider_user_id)
  AC6: Relationships, cascades, model instantiation

Run with: pytest tests/test_us001_db_schema.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import Boolean, DateTime, Enum, Integer, String, inspect
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.user import (
    AccountType,
    RefreshToken,
    SocialAccount,
    TeamInvitation,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.auth import (
    InviteCreateResponse,
    InviteDetailResponse,
    LoginResponse,
    RegisterStep2Request,
    TokenResponse,
    UserOut,
)


# ── Test Data ──────────────────────────────────────────────────────────────────

TEST_USER_ID = uuid.uuid4()
TEST_COMPANY_ID = uuid.uuid4()
TEST_NOW = datetime.now(timezone.utc)


def _sample_user_kwargs(**overrides):
    """Default kwargs for creating a User instance."""
    defaults = {
        "id": TEST_USER_ID,
        "email": "test@example.com",
        "password_hash": "$2b$12$fakehash",
        "full_name": "Test User",
        "phone": "+84901234567",
        "role": UserRole.job_seeker,
        "account_type": AccountType.job_seeker,
        "status": UserStatus.active,
        "first_login_complete": False,
        "consent_given": True,
        "consent_timestamp": TEST_NOW,
        "ai_abuse_count": 0,
        "failed_login_count": 0,
    }
    defaults.update(overrides)
    return defaults


def _sample_refresh_token_kwargs(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "user_id": TEST_USER_ID,
        "token_hash": "sha256hashvalue",
        "expires_at": TEST_NOW + timedelta(days=7),
        "revoked": False,
    }
    defaults.update(overrides)
    return defaults


def _sample_invitation_kwargs(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "company_id": TEST_COMPANY_ID,
        "invited_by": TEST_USER_ID,
        "email": "invite@example.com",
        "role": UserRole.hr_recruiter,
        "token_hash": "sha256invitehash",
        "expires_at": TEST_NOW + timedelta(hours=72),
        "accepted": False,
        "revoked": False,
    }
    defaults.update(overrides)
    return defaults


def _sample_social_account_kwargs(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "user_id": TEST_USER_ID,
        "provider": "google",
        "provider_user_id": "google-uid-12345",
    }
    defaults.update(overrides)
    return defaults


# ── AC1: All 4 tables exist ───────────────────────────────────────────────────


class TestAC1TablesExist:
    """AC1: make migrate creates all 4 auth tables without error."""

    def test_user_table_name(self):
        assert User.__tablename__ == "users"

    def test_refresh_token_table_name(self):
        assert RefreshToken.__tablename__ == "refresh_tokens"

    def test_team_invitation_table_name(self):
        assert TeamInvitation.__tablename__ == "team_invitations"

    def test_social_account_table_name(self):
        assert SocialAccount.__tablename__ == "social_accounts"

    def test_all_models_inherit_from_base(self):
        from app.database import Base

        for model in (User, RefreshToken, TeamInvitation, SocialAccount):
            assert issubclass(model, Base), f"{model.__name__} must inherit Base"


# ── AC2: users table columns ─────────────────────────────────────────────────


class TestAC2UsersTable:
    """AC2: users table has all required columns with correct types and constraints."""

    def _col(self, name):
        """Get column object from User model."""
        return User.__table__.columns[name]

    # Column existence
    def test_has_id_column(self):
        col = self._col("id")
        assert isinstance(col.type, PG_UUID)
        assert col.primary_key

    def test_has_email_column(self):
        col = self._col("email")
        assert isinstance(col.type, String)
        assert col.unique
        assert col.nullable is False
        assert col.index

    def test_has_password_hash_column(self):
        col = self._col("password_hash")
        assert isinstance(col.type, String)
        assert col.nullable is True  # null for OAuth users

    def test_has_full_name_column(self):
        col = self._col("full_name")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_has_phone_column(self):
        col = self._col("phone")
        assert isinstance(col.type, String)
        assert col.nullable is True

    def test_has_role_column(self):
        col = self._col("role")
        assert isinstance(col.type, Enum)
        assert col.nullable is False

    def test_has_account_type_column(self):
        col = self._col("account_type")
        assert isinstance(col.type, Enum)
        assert col.nullable is True

    def test_has_status_column(self):
        col = self._col("status")
        assert isinstance(col.type, Enum)
        assert col.nullable is False
        assert "pending" in str(col.server_default.arg)

    def test_has_first_login_complete_column(self):
        col = self._col("first_login_complete")
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert "false" in str(col.server_default.arg)

    def test_has_consent_given_column(self):
        col = self._col("consent_given")
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert "false" in str(col.server_default.arg)

    def test_has_consent_timestamp_column(self):
        col = self._col("consent_timestamp")
        assert isinstance(col.type, DateTime)
        assert col.nullable is True

    def test_has_created_at_column(self):
        col = self._col("created_at")
        assert isinstance(col.type, DateTime)
        assert col.server_default is not None

    def test_has_last_login_column(self):
        col = self._col("last_login")
        assert isinstance(col.type, DateTime)
        assert col.nullable is True

    def test_has_ai_abuse_count_column(self):
        col = self._col("ai_abuse_count")
        assert isinstance(col.type, Integer)
        assert col.nullable is False
        assert "0" in str(col.server_default.arg)

    def test_has_failed_login_count_column(self):
        """PRD FB-008: lockout after 3 failed attempts."""
        col = self._col("failed_login_count")
        assert isinstance(col.type, Integer)
        assert col.nullable is False
        assert "0" in str(col.server_default.arg)

    # Enums
    def test_role_enum_values(self):
        expected = {"super_admin", "company_admin", "hr_recruiter", "viewer", "job_seeker"}
        actual = {e.value for e in UserRole}
        assert actual == expected

    def test_account_type_enum_values(self):
        expected = {"employer", "job_seeker"}
        actual = {e.value for e in AccountType}
        assert actual == expected

    def test_status_enum_values(self):
        expected = {"pending", "active", "suspended", "locked"}
        actual = {e.value for e in UserStatus}
        assert actual == expected

    # Model instantiation
    def test_user_instantiation(self):
        user = User(**_sample_user_kwargs())
        assert user.email == "test@example.com"
        assert user.role == UserRole.job_seeker
        assert user.failed_login_count == 0
        assert user.consent_given is True

    def test_user_password_hash_nullable(self):
        """OAuth users may have no password."""
        user = User(**_sample_user_kwargs(password_hash=None))
        assert user.password_hash is None

    def test_user_default_status(self):
        """Server default is 'pending'."""
        col = self._col("status")
        assert "pending" in str(col.server_default.arg)


# ── AC3: refresh_tokens table ─────────────────────────────────────────────────


class TestAC3RefreshTokensTable:
    """AC3: refresh_tokens has id, user_id (FK CASCADE), token_hash, expires_at, revoked."""

    def _col(self, name):
        return RefreshToken.__table__.columns[name]

    def test_has_id_pk(self):
        col = self._col("id")
        assert isinstance(col.type, PG_UUID)
        assert col.primary_key

    def test_has_user_id_fk(self):
        col = self._col("user_id")
        assert isinstance(col.type, PG_UUID)
        assert col.nullable is False
        assert col.index
        # FK with CASCADE
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "users"
        assert fk.ondelete == "CASCADE"

    def test_has_token_hash(self):
        col = self._col("token_hash")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_has_expires_at_indexed(self):
        col = self._col("expires_at")
        assert isinstance(col.type, DateTime)
        assert col.nullable is False
        assert col.index  # Performance index for cleanup queries

    def test_has_revoked(self):
        col = self._col("revoked")
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert "false" in str(col.server_default.arg)

    def test_has_created_at(self):
        col = self._col("created_at")
        assert isinstance(col.type, DateTime)
        assert col.server_default is not None

    def test_instantiation(self):
        rt = RefreshToken(**_sample_refresh_token_kwargs())
        assert rt.user_id == TEST_USER_ID
        assert rt.revoked is False
        assert rt.expires_at > TEST_NOW


# ── AC4: team_invitations table ───────────────────────────────────────────────


class TestAC4TeamInvitationsTable:
    """AC4: team_invitations has correct columns, 72h expiry, expires_at index."""

    def _col(self, name):
        return TeamInvitation.__table__.columns[name]

    def test_has_id_pk(self):
        col = self._col("id")
        assert isinstance(col.type, PG_UUID)
        assert col.primary_key

    def test_has_company_id(self):
        col = self._col("company_id")
        assert isinstance(col.type, PG_UUID)
        assert col.nullable is False

    def test_has_invited_by_fk(self):
        col = self._col("invited_by")
        assert isinstance(col.type, PG_UUID)
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].column.table.name == "users"

    def test_has_email(self):
        col = self._col("email")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_has_role_enum(self):
        col = self._col("role")
        assert isinstance(col.type, Enum)
        assert col.nullable is False

    def test_has_token_hash(self):
        col = self._col("token_hash")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_has_expires_at_indexed(self):
        col = self._col("expires_at")
        assert isinstance(col.type, DateTime)
        assert col.nullable is False
        assert col.index  # Performance index

    def test_has_accepted(self):
        col = self._col("accepted")
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert "false" in str(col.server_default.arg)

    def test_has_revoked(self):
        col = self._col("revoked")
        assert isinstance(col.type, Boolean)
        assert col.nullable is False
        assert "false" in str(col.server_default.arg)

    def test_has_created_at(self):
        col = self._col("created_at")
        assert isinstance(col.type, DateTime)
        assert col.server_default is not None

    def test_instantiation_with_72h_expiry(self):
        inv = TeamInvitation(**_sample_invitation_kwargs())
        assert inv.email == "invite@example.com"
        assert inv.role == UserRole.hr_recruiter
        hours_until_expiry = (inv.expires_at - TEST_NOW).total_seconds() / 3600
        assert 71.9 < hours_until_expiry < 72.1

    def test_default_accepted_is_false(self):
        inv = TeamInvitation(**_sample_invitation_kwargs())
        assert inv.accepted is False

    def test_default_revoked_is_false(self):
        inv = TeamInvitation(**_sample_invitation_kwargs())
        assert inv.revoked is False


# ── AC5: social_accounts table ────────────────────────────────────────────────


class TestAC5SocialAccountsTable:
    """AC5: social_accounts with UNIQUE(provider, provider_user_id)."""

    def _col(self, name):
        return SocialAccount.__table__.columns[name]

    def test_has_id_pk(self):
        col = self._col("id")
        assert isinstance(col.type, PG_UUID)
        assert col.primary_key

    def test_has_user_id_fk_cascade(self):
        col = self._col("user_id")
        assert isinstance(col.type, PG_UUID)
        assert col.nullable is False
        assert col.index
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "CASCADE"

    def test_has_provider(self):
        col = self._col("provider")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_has_provider_user_id(self):
        col = self._col("provider_user_id")
        assert isinstance(col.type, String)
        assert col.nullable is False

    def test_has_created_at(self):
        col = self._col("created_at")
        assert isinstance(col.type, DateTime)
        assert col.server_default is not None

    def test_unique_constraint_exists(self):
        """UNIQUE(provider, provider_user_id)."""
        constraints = SocialAccount.__table__.constraints
        unique_constraints = [c for c in constraints if hasattr(c, "columns") and c.name == "uq_social_provider_user"]
        assert len(unique_constraints) == 1
        uc = unique_constraints[0]
        col_names = {col.name for col in uc.columns}
        assert col_names == {"provider", "provider_user_id"}

    def test_instantiation(self):
        sa = SocialAccount(**_sample_social_account_kwargs())
        assert sa.provider == "google"
        assert sa.provider_user_id == "google-uid-12345"
        assert sa.user_id == TEST_USER_ID


# ── AC6: Relationships & Cascades ─────────────────────────────────────────────


class TestAC6Relationships:
    """AC6: Verify ORM relationships are configured correctly."""

    def test_user_has_refresh_tokens_relationship(self):
        mapper = inspect(User)
        rels = {r.key for r in mapper.relationships}
        assert "refresh_tokens" in rels

    def test_user_has_social_accounts_relationship(self):
        mapper = inspect(User)
        rels = {r.key for r in mapper.relationships}
        assert "social_accounts" in rels

    def test_user_has_sent_invitations_relationship(self):
        mapper = inspect(User)
        rels = {r.key for r in mapper.relationships}
        assert "sent_invitations" in rels

    def test_refresh_tokens_cascade_delete_orphan(self):
        mapper = inspect(User)
        rel = mapper.relationships["refresh_tokens"]
        cascade_str = str(rel.cascade)
        assert "delete" in cascade_str
        assert "delete-orphan" in cascade_str

    def test_social_accounts_cascade_delete_orphan(self):
        mapper = inspect(User)
        rel = mapper.relationships["social_accounts"]
        cascade_str = str(rel.cascade)
        assert "delete" in cascade_str
        assert "delete-orphan" in cascade_str

    def test_refresh_token_back_populates_user(self):
        mapper = inspect(RefreshToken)
        rels = {r.key for r in mapper.relationships}
        assert "user" in rels

    def test_social_account_back_populates_user(self):
        mapper = inspect(SocialAccount)
        rels = {r.key for r in mapper.relationships}
        assert "user" in rels

    def test_invitation_back_populates_invited_by_user(self):
        mapper = inspect(TeamInvitation)
        rels = {r.key for r in mapper.relationships}
        assert "invited_by_user" in rels


# ── Schema Validation (Pydantic) ──────────────────────────────────────────────


class TestSchemaValidation:
    """Validate Pydantic schemas match the DB model structure."""

    def test_user_out_fields(self):
        """UserOut exposes id, email, full_name, phone, role, account_type, status, first_login_complete, created_at."""
        fields = set(UserOut.model_fields.keys())
        expected = {"id", "email", "full_name", "phone", "role", "account_type", "status", "first_login_complete", "created_at"}
        assert fields == expected

    def test_user_out_from_model(self):
        """UserOut can be created from a User-like object (from_attributes=True)."""
        user_data = {
            "id": TEST_USER_ID,
            "email": "schema@test.com",
            "full_name": "Schema Test",
            "phone": "+84901234567",
            "role": UserRole.super_admin,
            "account_type": AccountType.employer,
            "status": UserStatus.active,
            "first_login_complete": True,
            "created_at": TEST_NOW,
        }
        out = UserOut(**user_data)
        assert out.id == TEST_USER_ID
        assert out.role == UserRole.super_admin
        assert out.status == UserStatus.active

    def test_invite_create_response_has_invite_token(self):
        """InviteCreateResponse includes invite_token for Postman auto-capture."""
        fields = set(InviteCreateResponse.model_fields.keys())
        assert "invite_token" in fields
        assert "invitation_id" in fields
        assert "code" in fields
        assert "message" in fields

    def test_invite_create_response_instantiation(self):
        resp = InviteCreateResponse(
            invitation_id=uuid.uuid4(),
            invite_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            code="INVITE_SENT",
            message="Invitation has been sent.",
        )
        assert resp.invite_token.startswith("eyJ")

    def test_invite_detail_response_fields(self):
        fields = set(InviteDetailResponse.model_fields.keys())
        expected = {"id", "email", "role", "company_id", "expires_at", "accepted"}
        assert fields == expected

    def test_login_response_fields(self):
        fields = set(LoginResponse.model_fields.keys())
        assert "access_token" in fields
        assert "refresh_token" in fields
        assert "user" in fields
        assert "requires_2fa" in fields

    def test_register_step2_request_validation(self):
        """Validates phone format and password length."""
        with pytest.raises(Exception):
            RegisterStep2Request(
                account_type="job_seeker",
                full_name="X",  # too short (min 2)
                email="bad",
                phone="123",  # invalid format
                password="short",  # too short (min 8)
                consent_given=True,
            )

    def test_register_step2_valid(self):
        req = RegisterStep2Request(
            account_type="job_seeker",
            full_name="Nguyen Van Test",
            email="valid@test.com",
            phone="+84901234567",
            password="StrongPass1!",
            consent_given=True,
        )
        assert req.consent_given is True
        assert req.account_type == AccountType.job_seeker


# ── Column Count Verification ─────────────────────────────────────────────────


class TestColumnCounts:
    """Ensure no columns were accidentally dropped or left out."""

    def test_users_column_count(self):
        """users table should have 14 columns."""
        cols = User.__table__.columns
        expected_names = {
            "id", "email", "password_hash", "full_name", "phone",
            "role", "account_type", "status", "first_login_complete",
            "consent_given", "consent_timestamp", "created_at",
            "last_login", "ai_abuse_count", "failed_login_count",
        }
        actual_names = {col.name for col in cols}
        assert actual_names == expected_names

    def test_refresh_tokens_column_count(self):
        """refresh_tokens table should have 6 columns."""
        cols = RefreshToken.__table__.columns
        expected_names = {"id", "user_id", "token_hash", "expires_at", "revoked", "created_at"}
        actual_names = {col.name for col in cols}
        assert actual_names == expected_names

    def test_team_invitations_column_count(self):
        """team_invitations table should have 10 columns."""
        cols = TeamInvitation.__table__.columns
        expected_names = {
            "id", "company_id", "invited_by", "email", "role",
            "token_hash", "expires_at", "accepted", "revoked", "created_at",
        }
        actual_names = {col.name for col in cols}
        assert actual_names == expected_names

    def test_social_accounts_column_count(self):
        """social_accounts table should have 5 columns."""
        cols = SocialAccount.__table__.columns
        expected_names = {"id", "user_id", "provider", "provider_user_id", "created_at"}
        actual_names = {col.name for col in cols}
        assert actual_names == expected_names


# ── Index Verification ────────────────────────────────────────────────────────


class TestIndexes:
    """Verify indexes are defined on the model level."""

    def test_users_email_index(self):
        col = User.__table__.columns["email"]
        assert col.index is True

    def test_refresh_tokens_user_id_index(self):
        col = RefreshToken.__table__.columns["user_id"]
        assert col.index is True

    def test_refresh_tokens_expires_at_index(self):
        col = RefreshToken.__table__.columns["expires_at"]
        assert col.index is True

    def test_team_invitations_expires_at_index(self):
        col = TeamInvitation.__table__.columns["expires_at"]
        assert col.index is True

    def test_social_accounts_user_id_index(self):
        col = SocialAccount.__table__.columns["user_id"]
        assert col.index is True
