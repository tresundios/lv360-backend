"""company_job_tables

Create companies, jobs, applications, saved_jobs, events tables.
PF-004 — Seed Data Support
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum types ─────────────────────────────────────────────────────
    job_status_enum = sa.Enum(
        "draft", "published", "paused", "closed",
        name="job_status_enum",
    )
    job_status_enum.create(op.get_bind())

    application_status_enum = sa.Enum(
        "new", "screening", "interview", "offer", "hired", "rejected",
        name="application_status_enum",
    )
    application_status_enum.create(op.get_bind())

    employment_type_enum = sa.Enum(
        "full_time", "part_time", "contract", "internship", "freelance",
        name="employment_type_enum",
    )
    employment_type_enum.create(op.get_bind())

    experience_level_enum = sa.Enum(
        "entry", "junior", "mid", "senior", "lead", "executive",
        name="experience_level_enum",
    )
    experience_level_enum.create(op.get_bind())

    # ── Companies ─────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),
        sa.Column("verified", sa.Boolean, server_default="false", nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_companies_owner_id", "companies", ["owner_id"])

    # ── Jobs ──────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requirements", sa.Text, nullable=True),
        sa.Column("responsibilities", sa.Text, nullable=True),
        sa.Column("benefits", sa.Text, nullable=True),
        sa.Column("employment_type", employment_type_enum, nullable=False),
        sa.Column("experience_level", experience_level_enum, nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("remote_policy", sa.String(50), nullable=True),
        sa.Column("salary_min", sa.Integer, nullable=True),
        sa.Column("salary_max", sa.Integer, nullable=True),
        sa.Column("salary_currency", sa.String(3), nullable=True, server_default="VND"),
        sa.Column("status", job_status_enum, server_default="draft", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("applications_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("posted_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_jobs_company_id", "jobs", ["company_id"])
    op.create_index("ix_jobs_posted_by", "jobs", ["posted_by"])

    # ── Applications ───────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("status", application_status_enum, server_default="new", nullable=False),
        sa.Column("cover_letter", sa.Text, nullable=True),
        sa.Column("resume_url", sa.String(500), nullable=True),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("screened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interview_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("internal_notes", sa.Text, nullable=True),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_applications_job_id", "applications", ["job_id"])
    op.create_index("ix_applications_applicant_id", "applications", ["applicant_id"])

    # ── Saved Jobs ───────────────────────────────────────────────────────
    op.create_table(
        "saved_jobs",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # ── Events ───────────────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("all_day", sa.Boolean, server_default="false", nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("meeting_link", sa.String(500), nullable=True),
        sa.Column("related_job_id", UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("related_application_id", UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=True),
        sa.Column("attendee_ids", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_events_created_by", "events", ["created_by"])
    op.create_index("ix_events_start_time", "events", ["start_time"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("events")
    op.drop_table("saved_jobs")
    op.drop_table("applications")
    op.drop_table("jobs")
    op.drop_table("companies")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS experience_level_enum")
    op.execute("DROP TYPE IF EXISTS employment_type_enum")
    op.execute("DROP TYPE IF EXISTS application_status_enum")
    op.execute("DROP TYPE IF EXISTS job_status_enum")
