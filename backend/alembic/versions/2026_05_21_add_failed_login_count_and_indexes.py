"""add_failed_login_count_and_expires_at_indexes

Add users.failed_login_count column (AC2 — US-001).
Add indexes on refresh_tokens.expires_at and team_invitations.expires_at.
"""

from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add failed_login_count to users (PRD FB-008: lockout after 3 failed attempts)
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Performance indexes on expires_at columns
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_team_invitations_expires_at", "team_invitations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_team_invitations_expires_at", table_name="team_invitations")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_column("users", "failed_login_count")
