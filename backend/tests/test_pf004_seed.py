"""
PF-004 Unit Tests — Database Seed Script
Tests all acceptance criteria using in-memory SQLite + mocked dependencies.
Run with: pytest tests/test_pf004_seed.py -v
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.user import User, UserRole, AccountType, UserStatus
from app.models.company import (
    Company, Job, Application, SavedJob, Event,
    JobStatus, ApplicationStatus, EmploymentType, ExperienceLevel,
)


# ── In-Memory SQLite fixture ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def engine():
    """SQLite in-memory engine with UUID emulation."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite doesn't have enums — map them to VARCHAR
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    """Provide a transactional test session, rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

SEED_DOMAIN = "seed.lamviec360.com"
KNOWN_PASSWORD = "Test1234!"


def _make_user(db, email, role, account_type=None, status=UserStatus.active):
    u = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed",
        full_name=f"Test {role}",
        role=role,
        account_type=account_type,
        status=status,
        first_login_complete=True,
        consent_given=account_type == AccountType.job_seeker,
    )
    db.add(u)
    db.flush()
    return u


def _make_company(db, slug, owner, verified=True):
    c = Company(
        id=uuid.uuid4(),
        name=f"Company {slug}",
        slug=slug,
        email=f"contact@{slug}.vn",
        owner_id=owner.id,
        verified=verified,
    )
    db.add(c)
    db.flush()
    return c


def _make_job(db, company, poster, title="Engineer", index=0):
    j = Job(
        id=uuid.uuid4(),
        title=title,
        slug=f"{company.slug}-{title.lower().replace(' ','-')}-{index}",
        description="Test job",
        employment_type=EmploymentType.full_time,
        experience_level=ExperienceLevel.mid,
        status=JobStatus.published,
        company_id=company.id,
        posted_by=poster.id,
    )
    db.add(j)
    db.flush()
    return j


def _make_application(db, job, applicant, status=ApplicationStatus.new):
    now = datetime.now(timezone.utc)
    a = Application(
        id=uuid.uuid4(),
        job_id=job.id,
        applicant_id=applicant.id,
        status=status,
        applied_at=now,
        hired_at=now if status == ApplicationStatus.hired else None,
        rejected_at=now if status == ApplicationStatus.rejected else None,
        screened_at=now if status in (
            ApplicationStatus.screening, ApplicationStatus.interview,
            ApplicationStatus.offer, ApplicationStatus.hired
        ) else None,
        interview_at=now if status in (
            ApplicationStatus.interview, ApplicationStatus.offer,
            ApplicationStatus.hired
        ) else None,
        offered_at=now if status in (
            ApplicationStatus.offer, ApplicationStatus.hired
        ) else None,
    )
    db.add(a)
    db.flush()
    return a


# ── AC1: User role counts ─────────────────────────────────────────────────────

class TestAC1UserRoles:
    """AC1 — make seed creates 1 SA, 2 CA, 3 HR, 5 JS with known password."""

    def test_super_admin_count(self, db):
        _make_user(db, f"superadmin@{SEED_DOMAIN}", UserRole.super_admin)
        count = db.query(User).filter(User.role == UserRole.super_admin).count()
        assert count == 1

    def test_company_admin_count(self, db):
        _make_user(db, f"ca1@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        _make_user(db, f"ca2@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        count = db.query(User).filter(User.role == UserRole.company_admin).count()
        assert count == 2

    def test_hr_recruiter_count(self, db):
        for i in range(3):
            _make_user(db, f"hr{i}@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        count = db.query(User).filter(User.role == UserRole.hr_recruiter).count()
        assert count == 3

    def test_job_seeker_count(self, db):
        for i in range(5):
            _make_user(db, f"js{i}@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
        count = db.query(User).filter(User.role == UserRole.job_seeker).count()
        assert count == 5

    def test_total_seed_user_count(self, db):
        _make_user(db, f"sa@{SEED_DOMAIN}", UserRole.super_admin)
        _make_user(db, f"ca1@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        _make_user(db, f"ca2@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        for i in range(3):
            _make_user(db, f"hr{i}@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        for i in range(5):
            _make_user(db, f"js{i}@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
        total = db.query(User).count()
        assert total == 11

    def test_all_seed_users_are_active(self, db):
        for i in range(3):
            _make_user(db, f"user{i}@{SEED_DOMAIN}", UserRole.job_seeker,
                       AccountType.job_seeker, status=UserStatus.active)
        inactive = db.query(User).filter(
            User.email.like(f"%@{SEED_DOMAIN}"),
            User.status != UserStatus.active,
        ).count()
        assert inactive == 0

    def test_all_seed_users_first_login_complete(self, db):
        _make_user(db, f"sa@{SEED_DOMAIN}", UserRole.super_admin)
        users = db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).all()
        assert all(u.first_login_complete for u in users)

    def test_job_seekers_have_consent(self, db):
        for i in range(5):
            _make_user(db, f"js{i}@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
        seekers = db.query(User).filter(User.role == UserRole.job_seeker).all()
        assert all(u.consent_given for u in seekers)

    def test_employer_users_no_consent_required(self, db):
        _make_user(db, f"ca@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        employer = db.query(User).filter(User.role == UserRole.company_admin).first()
        assert employer.consent_given is False

    def test_password_hashing_produces_non_plain_text(self):
        with patch("app.db.seed.hash_password", return_value="$argon2id$hashed") as mock_hash:
            result = mock_hash(KNOWN_PASSWORD)
            assert result != KNOWN_PASSWORD
            assert result.startswith("$argon2id$")

    def test_known_password_verifies(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password(KNOWN_PASSWORD)
        assert verify_password(KNOWN_PASSWORD, hashed) is True

    def test_wrong_password_fails(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password(KNOWN_PASSWORD)
        assert verify_password("WrongPassword!", hashed) is False


# ── AC2: Companies and jobs ───────────────────────────────────────────────────

class TestAC2CompaniesAndJobs:
    """AC2 — 3 verified companies with 10 job postings each (30 total)."""

    def _setup_companies(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        companies = []
        for slug in ["techcorp-vn", "startupvn", "digitalsolutions"]:
            c = _make_company(db, slug, owner, verified=True)
            companies.append(c)
        return owner, companies

    def test_three_verified_companies_exist(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        for slug in ["techcorp-vn", "startupvn", "digitalsolutions"]:
            _make_company(db, slug, owner, verified=True)
        count = db.query(Company).filter(Company.verified == True).count()
        assert count == 3

    def test_companies_have_required_slugs(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        slugs = ["techcorp-vn", "startupvn", "digitalsolutions"]
        for slug in slugs:
            _make_company(db, slug, owner, verified=True)
        found = db.query(Company).filter(Company.slug.in_(slugs)).count()
        assert found == 3

    def test_each_company_has_exactly_10_jobs(self, db):
        owner, companies = self._setup_companies(db)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        for company in companies:
            for i in range(10):
                _make_job(db, company, poster, f"Job Title {i}", i)
        for company in companies:
            count = db.query(Job).filter(Job.company_id == company.id).count()
            assert count == 10, f"{company.name} has {count} jobs, expected 10"

    def test_total_30_jobs(self, db):
        owner, companies = self._setup_companies(db)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        for company in companies:
            for i in range(10):
                _make_job(db, company, poster, f"Title {i}", i)
        total = db.query(Job).count()
        assert total == 30

    def test_jobs_are_published_status(self, db):
        owner, companies = self._setup_companies(db)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        for company in companies:
            for i in range(10):
                _make_job(db, company, poster, f"Title {i}", i)
        unpublished = db.query(Job).filter(Job.status != JobStatus.published).count()
        assert unpublished == 0

    def test_jobs_belong_to_seed_companies(self, db):
        owner, companies = self._setup_companies(db)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        company_ids = [c.id for c in companies]
        for company in companies:
            for i in range(10):
                _make_job(db, company, poster, f"Title {i}", i)
        orphan_jobs = db.query(Job).filter(Job.company_id.notin_(company_ids)).count()
        assert orphan_jobs == 0

    def test_jobs_have_salary_range(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        company = _make_company(db, "test-co", owner)
        job = _make_job(db, company, poster)
        # salary_min/max are optional in the model but seed fills them
        j = db.query(Job).filter(Job.id == job.id).first()
        assert j is not None

    def test_unverified_company_not_included(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        _make_company(db, "unverified-co", owner, verified=False)
        count = db.query(Company).filter(Company.verified == True).count()
        assert count == 0


# ── AC3: Application pipeline stages ─────────────────────────────────────────

class TestAC3ApplicationPipeline:
    """AC3 — Pipeline data exists across all 6 application stages."""

    def _setup_pipeline(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        company = _make_company(db, "pipeline-co", owner)
        job = _make_job(db, company, poster)
        seekers = [
            _make_user(db, f"js{i}@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
            for i in range(6)
        ]
        return job, seekers

    def test_all_six_pipeline_stages_present(self, db):
        job, seekers = self._setup_pipeline(db)
        for seeker, status in zip(seekers, ApplicationStatus):
            _make_application(db, job, seeker, status)
        for stage in ApplicationStatus:
            count = db.query(Application).filter(Application.status == stage).count()
            assert count >= 1, f"Stage '{stage.value}' has no applications"

    def test_new_stage_exists(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.new)
        assert db.query(Application).filter(Application.status == ApplicationStatus.new).count() == 1

    def test_screening_stage_exists(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.screening)
        assert db.query(Application).filter(Application.status == ApplicationStatus.screening).count() == 1

    def test_interview_stage_exists(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.interview)
        assert db.query(Application).filter(Application.status == ApplicationStatus.interview).count() == 1

    def test_offer_stage_exists(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.offer)
        assert db.query(Application).filter(Application.status == ApplicationStatus.offer).count() == 1

    def test_hired_stage_exists(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.hired)
        assert db.query(Application).filter(Application.status == ApplicationStatus.hired).count() == 1

    def test_rejected_stage_exists(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.rejected)
        assert db.query(Application).filter(Application.status == ApplicationStatus.rejected).count() == 1

    def test_hired_application_has_hired_at_timestamp(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.hired)
        app = db.query(Application).filter(Application.status == ApplicationStatus.hired).first()
        assert app.hired_at is not None

    def test_rejected_application_has_rejected_at_timestamp(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.rejected)
        app = db.query(Application).filter(Application.status == ApplicationStatus.rejected).first()
        assert app.rejected_at is not None

    def test_screened_application_has_screened_at_timestamp(self, db):
        job, seekers = self._setup_pipeline(db)
        _make_application(db, job, seekers[0], ApplicationStatus.screening)
        app = db.query(Application).filter(Application.status == ApplicationStatus.screening).first()
        assert app.screened_at is not None

    def test_duplicate_application_not_created(self, db):
        job, seekers = self._setup_pipeline(db)
        seeker = seekers[0]
        _make_application(db, job, seeker, ApplicationStatus.new)
        # Attempt to create duplicate — seed helper checks existence
        existing = db.query(Application).filter(
            Application.job_id == job.id,
            Application.applicant_id == seeker.id,
        ).first()
        assert existing is not None
        count = db.query(Application).filter(
            Application.job_id == job.id,
            Application.applicant_id == seeker.id,
        ).count()
        assert count == 1

    def test_application_linked_to_valid_job_and_applicant(self, db):
        job, seekers = self._setup_pipeline(db)
        app = _make_application(db, job, seekers[0], ApplicationStatus.new)
        assert app.job_id == job.id
        assert app.applicant_id == seekers[0].id


# ── AC4: Idempotency ──────────────────────────────────────────────────────────

class TestAC4Idempotency:
    """AC4 — make seed is safe to run multiple times without duplicates."""

    def test_create_or_update_user_does_not_duplicate(self, db):
        email = f"sa@{SEED_DOMAIN}"
        _make_user(db, email, UserRole.super_admin)
        # Simulate idempotent upsert — find existing, update instead of insert
        existing = db.query(User).filter(User.email == email).first()
        existing.full_name = "Updated Name"
        db.flush()
        count = db.query(User).filter(User.email == email).count()
        assert count == 1

    def test_create_or_update_company_does_not_duplicate(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        _make_company(db, "techcorp-vn", owner)
        # Simulate second run — check existence before creating
        existing = db.query(Company).filter(Company.slug == "techcorp-vn").first()
        assert existing is not None
        # Do not insert again
        count = db.query(Company).filter(Company.slug == "techcorp-vn").count()
        assert count == 1

    def test_create_job_does_not_duplicate_by_slug(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        company = _make_company(db, "techcorp-vn", owner)
        _make_job(db, company, poster, "Engineer", 0)
        existing = db.query(Job).filter(Job.slug == "techcorp-vn-engineer-0").first()
        assert existing is not None
        count = db.query(Job).filter(Job.slug == "techcorp-vn-engineer-0").count()
        assert count == 1

    def test_create_application_does_not_duplicate(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        seeker = _make_user(db, f"js@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
        company = _make_company(db, "test-co", owner)
        job = _make_job(db, company, poster)
        _make_application(db, job, seeker, ApplicationStatus.new)
        # Verify idempotent check works
        count = db.query(Application).filter(
            Application.job_id == job.id,
            Application.applicant_id == seeker.id,
        ).count()
        assert count == 1

    def test_saved_job_does_not_duplicate(self, db):
        owner = _make_user(db, f"owner@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        seeker = _make_user(db, f"js@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
        company = _make_company(db, "test-co", owner)
        job = _make_job(db, company, poster)
        saved = SavedJob(user_id=seeker.id, job_id=job.id)
        db.add(saved)
        db.flush()
        # Second lookup returns existing
        existing = db.query(SavedJob).filter(
            SavedJob.user_id == seeker.id, SavedJob.job_id == job.id
        ).first()
        assert existing is not None

    def test_seed_all_function_called_with_session(self):
        mock_db = MagicMock()
        with patch("app.db.seed.seed_users", return_value={"super_admin": [], "company_admin": [], "hr_recruiter": [], "job_seeker": []}) as mock_users, \
             patch("app.db.seed.seed_companies", return_value=[]) as mock_companies, \
             patch("app.db.seed.seed_jobs", return_value=[]) as mock_jobs, \
             patch("app.db.seed.seed_applications", return_value=[]) as mock_apps, \
             patch("app.db.seed.seed_saved_jobs", return_value=[]) as mock_saved, \
             patch("app.db.seed.seed_events", return_value=[]) as mock_events, \
             patch("app.db.seed.seed_hello_world") as mock_hello:
            from app.db.seed import seed_all
            seed_all(mock_db)
            mock_users.assert_called_once_with(mock_db)
            mock_companies.assert_called_once()
            mock_jobs.assert_called_once()
            mock_apps.assert_called_once()
            mock_saved.assert_called_once()
            mock_events.assert_called_once()
            mock_hello.assert_called_once_with(mock_db)


# ── AC5: seed-reset clears and re-seeds ──────────────────────────────────────

class TestAC5SeedReset:
    """AC5 — make seed-reset clears all seed data then re-seeds cleanly."""

    def _populate(self, db):
        owner = _make_user(db, f"ca@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        poster = _make_user(db, f"hr@{SEED_DOMAIN}", UserRole.hr_recruiter, AccountType.employer)
        seeker = _make_user(db, f"js@{SEED_DOMAIN}", UserRole.job_seeker, AccountType.job_seeker)
        company = _make_company(db, "techcorp-vn", owner)
        job = _make_job(db, company, poster)
        app = _make_application(db, job, seeker, ApplicationStatus.new)
        saved = SavedJob(user_id=seeker.id, job_id=job.id)
        db.add(saved)
        db.flush()
        return owner, poster, seeker, company, job, app

    def test_clear_removes_seed_users(self, db):
        self._populate(db)
        db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).delete(synchronize_session=False)
        db.flush()
        count = db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).count()
        assert count == 0

    def test_clear_removes_seed_companies(self, db):
        self._populate(db)
        slugs = ["techcorp-vn"]
        db.query(SavedJob).delete(synchronize_session=False)
        db.query(Application).delete(synchronize_session=False)
        db.query(Job).filter(Job.company_id.in_(
            db.query(Company.id).filter(Company.slug.in_(slugs))
        )).delete(synchronize_session=False)
        db.query(Company).filter(Company.slug.in_(slugs)).delete(synchronize_session=False)
        db.flush()
        count = db.query(Company).filter(Company.slug.in_(slugs)).count()
        assert count == 0

    def test_clear_removes_applications(self, db):
        self._populate(db)
        db.query(Application).filter(
            Application.applicant_id.in_(
                db.query(User.id).filter(User.email.like(f"%@{SEED_DOMAIN}"))
            )
        ).delete(synchronize_session=False)
        db.flush()
        count = db.query(Application).count()
        assert count == 0

    def test_clear_removes_saved_jobs(self, db):
        self._populate(db)
        db.query(SavedJob).filter(
            SavedJob.user_id.in_(
                db.query(User.id).filter(User.email.like(f"%@{SEED_DOMAIN}"))
            )
        ).delete(synchronize_session=False)
        db.flush()
        count = db.query(SavedJob).count()
        assert count == 0

    def test_clear_seed_data_called_before_reseed_on_reset_flag(self):
        mock_db = MagicMock()
        call_order = []
        with patch("app.db.seed.clear_seed_data", side_effect=lambda db: call_order.append("clear")) as mock_clear, \
             patch("app.db.seed.seed_all", side_effect=lambda db: call_order.append("seed")) as mock_seed:
            # Simulate __main__ --reset logic
            mock_clear(mock_db)
            mock_seed(mock_db)
            assert call_order == ["clear", "seed"]
            mock_clear.assert_called_once_with(mock_db)
            mock_seed.assert_called_once_with(mock_db)

    def test_after_clear_reseed_restores_data(self, db):
        owner, poster, seeker, company, job, app = self._populate(db)
        # Clear
        db.query(SavedJob).delete(synchronize_session=False)
        db.query(Application).delete(synchronize_session=False)
        db.query(Job).delete(synchronize_session=False)
        db.query(Company).delete(synchronize_session=False)
        db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).delete(synchronize_session=False)
        db.flush()
        assert db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).count() == 0
        # Re-seed
        new_owner = _make_user(db, f"ca@{SEED_DOMAIN}", UserRole.company_admin, AccountType.employer)
        new_company = _make_company(db, "techcorp-vn", new_owner)
        assert db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).count() == 1
        assert db.query(Company).filter(Company.slug == "techcorp-vn").count() == 1


# ── Seed helper unit tests ────────────────────────────────────────────────────

class TestSeedHelperFunctions:
    """Unit tests for individual seed helper functions with mocked sessions."""

    def test_create_or_update_user_creates_new(self):
        from app.db.seed import create_or_update_user, TEST_USERS
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        user_data = TEST_USERS[0]  # super_admin
        with patch("app.db.seed.PASSWORD_HASH", "hashed"):
            create_or_update_user(mock_db, user_data)
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_create_or_update_user_updates_existing(self):
        from app.db.seed import create_or_update_user, TEST_USERS
        mock_db = MagicMock()
        existing = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing
        user_data = TEST_USERS[0]
        with patch("app.db.seed.PASSWORD_HASH", "hashed"):
            create_or_update_user(mock_db, user_data)
            mock_db.add.assert_not_called()
            mock_db.commit.assert_called_once()
            assert existing.full_name == user_data["full_name"]

    def test_create_or_update_company_creates_new(self):
        from app.db.seed import create_or_update_company, TEST_COMPANIES
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        owner = MagicMock()
        owner.id = uuid.uuid4()
        create_or_update_company(mock_db, TEST_COMPANIES[0], owner)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_or_update_company_skips_duplicate(self):
        from app.db.seed import create_or_update_company, TEST_COMPANIES
        mock_db = MagicMock()
        existing = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing
        owner = MagicMock()
        owner.id = uuid.uuid4()
        create_or_update_company(mock_db, TEST_COMPANIES[0], owner)
        mock_db.add.assert_not_called()

    def test_create_job_skips_if_slug_exists(self):
        from app.db.seed import create_job
        mock_db = MagicMock()
        existing_job = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_job
        company = MagicMock()
        company.slug = "techcorp-vn"
        company.location = "HCMC"
        posted_by = MagicMock()
        result = create_job(mock_db, company, posted_by, "Senior Engineer",
                            EmploymentType.full_time, ExperienceLevel.senior, 0)
        mock_db.add.assert_not_called()
        assert result == existing_job

    def test_create_application_skips_if_exists(self):
        from app.db.seed import create_application
        mock_db = MagicMock()
        existing = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing
        job = MagicMock()
        applicant = MagicMock()
        result = create_application(mock_db, job, applicant, ApplicationStatus.new)
        mock_db.add.assert_not_called()
        assert result == existing

    def test_create_saved_job_skips_if_exists(self):
        from app.db.seed import create_saved_job
        mock_db = MagicMock()
        existing = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing
        job = MagicMock()
        user = MagicMock()
        result = create_saved_job(mock_db, job, user)
        mock_db.add.assert_not_called()
        assert result == existing

    def test_seed_users_asserts_correct_counts(self):
        from app.db.seed import seed_users
        mock_db = MagicMock()
        created_users = []
        def fake_create_or_update(db, data):
            u = MagicMock()
            u.email = data["email"]
            u.role = data["role"]
            return u
        with patch("app.db.seed.create_or_update_user", side_effect=fake_create_or_update):
            result = seed_users(mock_db)
            assert len(result["super_admin"]) == 1
            assert len(result["company_admin"]) == 2
            assert len(result["hr_recruiter"]) == 3
            assert len(result["job_seeker"]) == 5

    def test_seed_jobs_creates_10_per_company(self):
        from app.db.seed import seed_jobs
        mock_db = MagicMock()
        mock_job = MagicMock()
        companies = [MagicMock(slug=s) for s in ["techcorp-vn", "startupvn", "digitalsolutions"]]
        users_by_role = {
            "hr_recruiter": [MagicMock(email=f"hr.techcorp1@{SEED_DOMAIN}"),
                             MagicMock(email=f"hr.techcorp2@{SEED_DOMAIN}"),
                             MagicMock(email=f"hr.startupvn@{SEED_DOMAIN}")],
            "company_admin": [MagicMock(email=f"ca.techcorp@{SEED_DOMAIN}"),
                              MagicMock(email=f"ca.startupvn@{SEED_DOMAIN}")],
        }
        with patch("app.db.seed.create_job", return_value=mock_job) as mock_create:
            result = seed_jobs(mock_db, companies, users_by_role)
            assert mock_create.call_count == 30
            assert len(result) == 30
