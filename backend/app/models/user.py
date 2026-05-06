"""
Auth SQLAlchemy models — PRD Section 3.1
Tables: users, refresh_tokens, team_invitations, social_accounts
"""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ── Enums ──────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    company_admin = "company_admin"
    hr_recruiter = "hr_recruiter"
    viewer = "viewer"
    job_seeker = "job_seeker"


class AccountType(str, enum.Enum):
    employer = "employer"
    job_seeker = "job_seeker"


class UserStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


# ── Users ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # null for OAuth users
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(Enum(UserRole, name="user_role_enum", create_type=False), nullable=False)
    account_type = Column(Enum(AccountType, name="account_type_enum", create_type=False), nullable=True)
    status = Column(
        Enum(UserStatus, name="user_status_enum", create_type=False),
        nullable=False,
        server_default="pending",
    )
    first_login_complete = Column(Boolean, server_default="false", nullable=False)
    consent_given = Column(Boolean, server_default="false", nullable=False)
    consent_timestamp = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    ai_abuse_count = Column(Integer, server_default="0", nullable=False)

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    social_accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    sent_invitations = relationship("TeamInvitation", back_populates="invited_by_user", foreign_keys="TeamInvitation.invited_by")
    
    # Company/Job relationships (added for PF-004)
    companies = relationship("Company", back_populates="owner", cascade="all, delete-orphan")
    posted_jobs = relationship("Job", back_populates="poster")
    applications = relationship("Application", back_populates="applicant", cascade="all, delete-orphan")
    saved_jobs = relationship("SavedJob", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="creator", cascade="all, delete-orphan")


# ── Refresh Tokens ─────────────────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")


# ── Team Invitations ───────────────────────────────────────────────────

class TeamInvitation(Base):
    __tablename__ = "team_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False)
    role = Column(Enum(UserRole, name="user_role_enum", create_type=False), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted = Column(Boolean, server_default="false", nullable=False)
    revoked = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invited_by_user = relationship("User", back_populates="sent_invitations", foreign_keys=[invited_by])


# ── Social Accounts ────────────────────────────────────────────────────

class SocialAccount(Base):
    __tablename__ = "social_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)  # CHECK in migration
    provider_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="social_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_provider_user"),
    )
