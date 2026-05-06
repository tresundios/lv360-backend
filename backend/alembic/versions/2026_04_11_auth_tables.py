"""auth_tables

Create users, refresh_tokens, team_invitations, social_accounts tables.
PRD Section 3.1 — AUTH-FR-001 to AUTH-FR-009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "a1b2c3d4e5f6"
down_revision = "20260310_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum types ─────────────────────────────────────────────────────
    user_role_enum = sa.Enum(
        "super_admin", "company_admin", "hr_recruiter", "viewer", "job_seeker",
        name="user_role_enum",
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    account_type_enum = sa.Enum("employer", "job_seeker", name="account_type_enum")
    account_type_enum.create(op.get_bind(), checkfirst=True)

    user_status_enum = sa.Enum("pending", "active", "suspended", name="user_status_enum")
    user_status_enum.create(op.get_bind(), checkfirst=True)

    # ── users ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("account_type", account_type_enum, nullable=True),
        sa.Column("status", user_status_enum, nullable=False, server_default="pending"),
        sa.Column("first_login_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_abuse_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── refresh_tokens ─────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── team_invitations ───────────────────────────────────────────────
    op.create_table(
        "team_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now() + interval '72 hours'")),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── social_accounts ────────────────────────────────────────────────
    op.create_table(
        "social_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),
        sa.CheckConstraint("provider IN ('google', 'zalo')", name="ck_social_provider"),
    )


def downgrade() -> None:
    op.drop_table("social_accounts")
    op.drop_table("team_invitations")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    sa.Enum(name="user_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="account_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
