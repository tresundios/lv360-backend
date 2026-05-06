"""
Company and Job SQLAlchemy models — PF-004 Seed Data Support
Tables: companies, jobs, applications, saved_jobs, events
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ── Enums ──────────────────────────────────────────────────────────────

class JobStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    paused = "paused"
    closed = "closed"


class ApplicationStatus(str, enum.Enum):
    new = "new"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"


class EmploymentType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    freelance = "freelance"


class ExperienceLevel(str, enum.Enum):
    entry = "entry"
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    executive = "executive"


# ── Companies ─────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    industry = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    company_size = Column(String(50), nullable=True)  # e.g., "1-50", "51-200", etc.
    verified = Column(Boolean, server_default="false", nullable=False)
    
    # Contact info
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="companies")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")


# ── Jobs ──────────────────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    benefits = Column(Text, nullable=True)
    
    # Job details
    employment_type = Column(Enum(EmploymentType, name="employment_type_enum", create_type=False), nullable=False)
    experience_level = Column(Enum(ExperienceLevel, name="experience_level_enum", create_type=False), nullable=True)
    location = Column(String(255), nullable=True)
    remote_policy = Column(String(50), nullable=True)  # onsite, hybrid, remote
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(3), nullable=True, server_default="VND")
    
    # Status
    status = Column(Enum(JobStatus, name="job_status_enum", create_type=False), server_default="draft", nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    views_count = Column(Integer, server_default="0", nullable=False)
    applications_count = Column(Integer, server_default="0", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    posted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="jobs")
    poster = relationship("User", back_populates="posted_jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    saved_by = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")


# ── Applications (Pipeline) ───────────────────────────────────────────

class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Pipeline status
    status = Column(Enum(ApplicationStatus, name="application_status_enum", create_type=False), server_default="new", nullable=False)
    
    # Application details
    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    
    # Pipeline timestamps
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    screened_at = Column(DateTime(timezone=True), nullable=True)
    interview_at = Column(DateTime(timezone=True), nullable=True)
    offered_at = Column(DateTime(timezone=True), nullable=True)
    hired_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Rejection reason
    rejection_reason = Column(Text, nullable=True)
    
    # Internal notes
    internal_notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 star rating
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    applicant = relationship("User", back_populates="applications")


# ── Saved Jobs ───────────────────────────────────────────────────────

class SavedJob(Base):
    __tablename__ = "saved_jobs"
    
    # Composite primary key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    
    saved_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by")


# ── Events ────────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Event type
    event_type = Column(String(50), nullable=False)  # interview, meeting, deadline, reminder, etc.
    
    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    all_day = Column(Boolean, server_default="false", nullable=False)
    
    # Location (physical or virtual)
    location = Column(String(255), nullable=True)
    meeting_link = Column(String(500), nullable=True)
    
    # Related entities
    related_job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True)
    related_application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True)
    
    # Attendees (stored as JSON array of user IDs for simplicity)
    attendee_ids = Column(Text, nullable=True)
    
    # Creator
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User", back_populates="events")
    related_job = relationship("Job")
    related_application = relationship("Application")
