"""
PF-004 — Comprehensive Database Seed Script
Creates test users, companies, jobs, applications, saved jobs, and events.
Idempotent — safe to run multiple times.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import (
    User,
    UserRole,
    AccountType,
    UserStatus,
    Company,
    Job,
    Application,
    SavedJob,
    Event,
    JobStatus,
    ApplicationStatus,
    EmploymentType,
    ExperienceLevel,
    HelloWorld,
    Task,
)
from app.core.security import hash_password


# ── Configuration ─────────────────────────────────────────────────────

KNOWN_PASSWORD = "Test1234!"  # All test users use this password
PASSWORD_HASH = hash_password(KNOWN_PASSWORD)

SEED_EMAIL_DOMAIN = "seed.lamviec360.com"

# Mark seed data for easy cleanup
SEED_MARKER = "[SEED]"


# ── Test User Data ────────────────────────────────────────────────────

TEST_USERS = [
    # Super Admin (1)
    {
        "email": f"superadmin@{SEED_EMAIL_DOMAIN}",
        "full_name": "Super Admin",
        "phone": "+84900000001",
        "role": UserRole.super_admin,
        "account_type": None,
    },
    # Company Admins (2)
    {
        "email": f"ca.techcorp@{SEED_EMAIL_DOMAIN}",
        "full_name": "Nguyen Van A - TechCorp Admin",
        "phone": "+84900000002",
        "role": UserRole.company_admin,
        "account_type": AccountType.employer,
    },
    {
        "email": f"ca.startupvn@{SEED_EMAIL_DOMAIN}",
        "full_name": "Tran Thi B - StartupVN Admin",
        "phone": "+84900000003",
        "role": UserRole.company_admin,
        "account_type": AccountType.employer,
    },
    # HR Recruiters (3)
    {
        "email": f"hr.techcorp1@{SEED_EMAIL_DOMAIN}",
        "full_name": "Le Van C - TechCorp HR",
        "phone": "+84900000004",
        "role": UserRole.hr_recruiter,
        "account_type": AccountType.employer,
    },
    {
        "email": f"hr.techcorp2@{SEED_EMAIL_DOMAIN}",
        "full_name": "Pham Thi D - TechCorp HR",
        "phone": "+84900000005",
        "role": UserRole.hr_recruiter,
        "account_type": AccountType.employer,
    },
    {
        "email": f"hr.startupvn@{SEED_EMAIL_DOMAIN}",
        "full_name": "Hoang Van E - StartupVN HR",
        "phone": "+84900000006",
        "role": UserRole.hr_recruiter,
        "account_type": AccountType.employer,
    },
    # Job Seekers (5)
    {
        "email": f"js.01@{SEED_EMAIL_DOMAIN}",
        "full_name": "Nguyen Thi Ha",
        "phone": "+84900000007",
        "role": UserRole.job_seeker,
        "account_type": AccountType.job_seeker,
    },
    {
        "email": f"js.02@{SEED_EMAIL_DOMAIN}",
        "full_name": "Tran Van Hieu",
        "phone": "+84900000008",
        "role": UserRole.job_seeker,
        "account_type": AccountType.job_seeker,
    },
    {
        "email": f"js.03@{SEED_EMAIL_DOMAIN}",
        "full_name": "Le Thi Linh",
        "phone": "+84900000009",
        "role": UserRole.job_seeker,
        "account_type": AccountType.job_seeker,
    },
    {
        "email": f"js.04@{SEED_EMAIL_DOMAIN}",
        "full_name": "Pham Van Minh",
        "phone": "+84900000010",
        "role": UserRole.job_seeker,
        "account_type": AccountType.job_seeker,
    },
    {
        "email": f"js.05@{SEED_EMAIL_DOMAIN}",
        "full_name": "Hoang Thi Ngoc",
        "phone": "+84900000011",
        "role": UserRole.job_seeker,
        "account_type": AccountType.job_seeker,
    },
]


# ── Test Company Data ─────────────────────────────────────────────────

TEST_COMPANIES = [
    {
        "slug": "techcorp-vn",
        "name": "TechCorp Vietnam",
        "description": "Leading technology company in Vietnam specializing in software development and AI solutions.",
        "website": "https://techcorp.vn",
        "industry": "Information Technology",
        "location": "Ho Chi Minh City",
        "company_size": "501-1000",
        "verified": True,
        "owner_email": f"ca.techcorp@{SEED_EMAIL_DOMAIN}",
    },
    {
        "slug": "startupvn",
        "name": "StartupVN",
        "description": "Fast-growing startup focusing on fintech and e-commerce solutions.",
        "website": "https://startupvn.io",
        "industry": "Financial Technology",
        "location": "Ho Chi Minh City",
        "company_size": "51-200",
        "verified": True,
        "owner_email": f"ca.startupvn@{SEED_EMAIL_DOMAIN}",
    },
    {
        "slug": "digitalsolutions",
        "name": "Digital Solutions Ltd",
        "description": "Digital transformation consultancy and software development firm.",
        "website": "https://digitalsolutions.vn",
        "industry": "Consulting",
        "location": "Ha Noi",
        "company_size": "201-500",
        "verified": True,
        "owner_email": f"ca.techcorp@{SEED_EMAIL_DOMAIN}",  # Same owner as TechCorp for demo
    },
]


# ── Test Job Templates ────────────────────────────────────────────────

JOB_TITLES = [
    "Senior Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "DevOps Engineer",
    "Product Manager",
    "UI/UX Designer",
    "Data Engineer",
    "QA Engineer",
    "Mobile Developer",
]

JOB_DESCRIPTION_TEMPLATE = """
## About the Role

We are looking for a talented {title} to join our growing team. You will work on exciting projects and collaborate with skilled professionals.

## Responsibilities

- Develop and maintain high-quality software
- Collaborate with cross-functional teams
- Participate in code reviews and technical discussions
- Contribute to system architecture decisions

## Requirements

- 2+ years of relevant experience
- Strong problem-solving skills
- Good communication in English
- Passion for learning new technologies

## Benefits

- Competitive salary
- Health insurance
- Flexible working hours
- Remote work options
- Professional development budget
"""

EMPLOYMENT_TYPES = [
    EmploymentType.full_time,
    EmploymentType.full_time,
    EmploymentType.full_time,
    EmploymentType.contract,
    EmploymentType.full_time,
    EmploymentType.full_time,
    EmploymentType.full_time,
    EmploymentType.full_time,
    EmploymentType.full_time,
    EmploymentType.full_time,
]

EXPERIENCE_LEVELS = [
    ExperienceLevel.senior,
    ExperienceLevel.mid,
    ExperienceLevel.mid,
    ExperienceLevel.mid,
    ExperienceLevel.senior,
    ExperienceLevel.senior,
    ExperienceLevel.mid,
    ExperienceLevel.senior,
    ExperienceLevel.junior,
    ExperienceLevel.mid,
]


# ── Event Types ───────────────────────────────────────────────────────

EVENT_TYPES = ["interview", "meeting", "deadline", "reminder", "follow_up"]


# ── Helper Functions ─────────────────────────────────────────────────

def get_seed_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get a seed user by email."""
    return db.query(User).filter(User.email == email).first()


def create_or_update_user(db: Session, user_data: dict) -> User:
    """Create or update a seed user."""
    existing = get_seed_user_by_email(db, user_data["email"])
    
    if existing:
        # Update existing user
        existing.full_name = user_data["full_name"]
        existing.phone = user_data["phone"]
        existing.role = user_data["role"]
        existing.account_type = user_data["account_type"]
        existing.password_hash = PASSWORD_HASH
        existing.status = UserStatus.active
        existing.first_login_complete = True
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new user
    user = User(
        email=user_data["email"],
        password_hash=PASSWORD_HASH,
        full_name=user_data["full_name"],
        phone=user_data["phone"],
        role=user_data["role"],
        account_type=user_data["account_type"],
        status=UserStatus.active,
        first_login_complete=True,
        consent_given=True if user_data["account_type"] == AccountType.job_seeker else False,
        consent_timestamp=datetime.now(timezone.utc) if user_data["account_type"] == AccountType.job_seeker else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_or_update_company(db: Session, company_data: dict, owner: User) -> Company:
    """Create or update a seed company."""
    existing = db.query(Company).filter(Company.slug == company_data["slug"]).first()
    
    if existing:
        existing.name = company_data["name"]
        existing.description = company_data["description"]
        existing.website = company_data["website"]
        existing.industry = company_data["industry"]
        existing.location = company_data["location"]
        existing.company_size = company_data["company_size"]
        existing.verified = company_data["verified"]
        existing.owner_id = owner.id
        db.commit()
        db.refresh(existing)
        return existing
    
    company = Company(
        slug=company_data["slug"],
        name=company_data["name"],
        description=company_data["description"],
        website=company_data["website"],
        industry=company_data["industry"],
        location=company_data["location"],
        company_size=company_data["company_size"],
        verified=company_data["verified"],
        owner_id=owner.id,
        email=f"contact@{company_data['slug']}.vn",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def create_job(db: Session, company: Company, posted_by: User, title: str, 
               employment_type: EmploymentType, experience_level: ExperienceLevel,
               index: int) -> Job:
    """Create a seed job posting."""
    slug = f"{company.slug}-{title.lower().replace(' ', '-')}-{index}"
    
    # Check if job exists
    existing = db.query(Job).filter(Job.slug == slug).first()
    if existing:
        return existing
    
    description = JOB_DESCRIPTION_TEMPLATE.format(title=title)
    
    # Salary ranges based on experience
    salary_ranges = {
        ExperienceLevel.entry: (8_000_000, 12_000_000),
        ExperienceLevel.junior: (12_000_000, 18_000_000),
        ExperienceLevel.mid: (18_000_000, 30_000_000),
        ExperienceLevel.senior: (30_000_000, 50_000_000),
        ExperienceLevel.lead: (45_000_000, 70_000_000),
        ExperienceLevel.executive: (60_000_000, 100_000_000),
    }
    
    salary_min, salary_max = salary_ranges.get(experience_level, (20_000_000, 40_000_000))
    
    job = Job(
        slug=slug,
        title=title,
        description=description,
        requirements="See job description",
        responsibilities="See job description",
        benefits="Competitive salary, health insurance, flexible hours",
        employment_type=employment_type,
        experience_level=experience_level,
        location=company.location,
        remote_policy="hybrid" if index % 3 == 0 else "onsite" if index % 3 == 1 else "remote",
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency="VND",
        status=JobStatus.published,
        published_at=datetime.now(timezone.utc) - timedelta(days=index),
        company_id=company.id,
        posted_by=posted_by.id,
        views_count=100 + index * 50,
        applications_count=5 + index * 3,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_application(db: Session, job: Job, applicant: User, status: ApplicationStatus,
                       days_ago: int = 0) -> Application:
    """Create a seed job application."""
    # Check if application exists
    existing = db.query(Application).filter(
        Application.job_id == job.id,
        Application.applicant_id == applicant.id,
    ).first()
    
    if existing:
        return existing
    
    applied_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    app = Application(
        job_id=job.id,
        applicant_id=applicant.id,
        status=status,
        cover_letter=f"I am very interested in the {job.title} position at your company. I have relevant experience and skills.",
        applied_at=applied_at,
        screened_at=applied_at + timedelta(days=2) if status.value in ["screening", "interview", "offer", "hired"] else None,
        interview_at=applied_at + timedelta(days=5) if status.value in ["interview", "offer", "hired"] else None,
        offered_at=applied_at + timedelta(days=10) if status.value in ["offer", "hired"] else None,
        hired_at=applied_at + timedelta(days=14) if status.value == "hired" else None,
        rejected_at=applied_at + timedelta(days=7) if status.value == "rejected" else None,
        rating=4 if status.value in ["hired", "offer"] else 3 if status.value == "interview" else None,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def create_saved_job(db: Session, job: Job, user: User) -> SavedJob:
    """Create a seed saved job."""
    existing = db.query(SavedJob).filter(
        SavedJob.user_id == user.id,
        SavedJob.job_id == job.id,
    ).first()
    
    if existing:
        return existing
    
    saved = SavedJob(
        user_id=user.id,
        job_id=job.id,
        notes="Interesting opportunity" if user.id.int % 2 == 0 else None,
    )
    db.add(saved)
    db.commit()
    return saved


def create_event(db: Session, created_by: User, title: str, event_type: str,
                 days_from_now: int = 0, related_job: Optional[Job] = None,
                 related_application: Optional[Application] = None) -> Event:
    """Create a seed calendar event."""
    start_time = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    
    existing = db.query(Event).filter(
        Event.title == title,
        Event.created_by == created_by.id,
        Event.start_time == start_time,
    ).first()
    
    if existing:
        return existing
    
    event = Event(
        title=title,
        description=f"{event_type.capitalize()} event for {title}",
        event_type=event_type,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1) if not event_type == "deadline" else None,
        all_day=event_type == "deadline",
        location="Ho Chi Minh City" if event_type in ["interview", "meeting"] else None,
        meeting_link=f"https://meet.lamviec360.com/{uuid.uuid4().hex[:8]}" if event_type in ["interview", "meeting"] else None,
        related_job_id=related_job.id if related_job else None,
        related_application_id=related_application.id if related_application else None,
        attendee_ids=str([created_by.id]) if created_by else None,
        created_by=created_by.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ── Main Seed Functions ──────────────────────────────────────────────

def seed_users(db: Session) -> dict:
    """Create all test users. Returns dict mapping role to list of users."""
    print("[SEED] Creating test users...")
    
    users_by_role = {
        "super_admin": [],
        "company_admin": [],
        "hr_recruiter": [],
        "job_seeker": [],
    }
    
    for user_data in TEST_USERS:
        user = create_or_update_user(db, user_data)
        role_key = user_data["role"].value
        if role_key in users_by_role:
            users_by_role[role_key].append(user)
        print(f"  ✓ {user.email} ({user.role.value})")
    
    # Verify counts
    assert len(users_by_role["super_admin"]) == 1, "Expected 1 super_admin"
    assert len(users_by_role["company_admin"]) == 2, "Expected 2 company_admin"
    assert len(users_by_role["hr_recruiter"]) == 3, "Expected 3 hr_recruiter"
    assert len(users_by_role["job_seeker"]) == 5, "Expected 5 job_seeker"
    
    print(f"[SEED] Created {len(TEST_USERS)} test users")
    return users_by_role


def seed_companies(db: Session, users_by_role: dict) -> list:
    """Create test companies."""
    print("[SEED] Creating test companies...")
    
    companies = []
    for company_data in TEST_COMPANIES:
        owner = get_seed_user_by_email(db, company_data["owner_email"])
        if not owner:
            print(f"  ⚠ Owner not found for {company_data['name']}")
            continue
        
        company = create_or_update_company(db, company_data, owner)
        companies.append(company)
        print(f"  ✓ {company.name} (owner: {owner.full_name})")
    
    print(f"[SEED] Created {len(companies)} test companies")
    return companies


def seed_jobs(db: Session, companies: list, users_by_role: dict) -> list:
    """Create 10 jobs per company (30 total)."""
    print("[SEED] Creating test jobs...")
    
    all_hr_recruiters = users_by_role["hr_recruiter"]
    all_jobs = []
    
    job_index = 0
    for company in companies:
        # Assign HR recruiter based on company ownership
        company_owner_email = next(
            (c["owner_email"] for c in TEST_COMPANIES if c["slug"] == company.slug),
            None
        )
        
        # Find appropriate poster (HR or Company Admin from that company)
        if "techcorp" in company.slug:
            posters = [u for u in all_hr_recruiters if "techcorp" in u.email] + \
                     [u for u in users_by_role["company_admin"] if "techcorp" in u.email]
        elif "startupvn" in company.slug:
            posters = [u for u in all_hr_recruiters if "startupvn" in u.email] + \
                     [u for u in users_by_role["company_admin"] if "startupvn" in u.email]
        else:
            posters = all_hr_recruiters + users_by_role["company_admin"]
        
        poster = posters[0] if posters else all_hr_recruiters[0]
        
        for i in range(10):
            title = JOB_TITLES[job_index % len(JOB_TITLES)]
            employment_type = EMPLOYMENT_TYPES[job_index % len(EMPLOYMENT_TYPES)]
            experience_level = EXPERIENCE_LEVELS[job_index % len(EXPERIENCE_LEVELS)]
            
            job = create_job(db, company, poster, title, employment_type, experience_level, job_index)
            all_jobs.append(job)
            job_index += 1
    
    print(f"[SEED] Created {len(all_jobs)} test jobs")
    return all_jobs


def seed_applications(db: Session, jobs: list, users_by_role: dict) -> list:
    """Create applications with pipeline data across all stages."""
    print("[SEED] Creating test applications...")
    
    job_seekers = users_by_role["job_seeker"]
    all_applications = []
    
    # Define status distribution for realistic pipeline
    status_distribution = [
        ApplicationStatus.new,
        ApplicationStatus.new,
        ApplicationStatus.screening,
        ApplicationStatus.screening,
        ApplicationStatus.interview,
        ApplicationStatus.interview,
        ApplicationStatus.offer,
        ApplicationStatus.hired,
        ApplicationStatus.rejected,
        ApplicationStatus.rejected,
    ]
    
    app_index = 0
    for job in jobs[:15]:  # Only apply to first 15 jobs to keep it realistic
        for seeker in job_seekers:
            # Not every seeker applies to every job
            if (seeker.id.int + job.id.int) % 3 != 0:
                continue
            
            status = status_distribution[app_index % len(status_distribution)]
            days_ago = app_index % 20
            
            app = create_application(db, job, seeker, status, days_ago)
            all_applications.append(app)
            app_index += 1
    
    print(f"[SEED] Created {len(all_applications)} test applications")
    return all_applications


def seed_saved_jobs(db: Session, jobs: list, users_by_role: dict) -> list:
    """Create saved jobs for job seekers."""
    print("[SEED] Creating saved jobs...")
    
    job_seekers = users_by_role["job_seeker"]
    all_saved = []
    
    for seeker in job_seekers:
        # Each seeker saves 3-5 jobs
        num_saves = 3 + (seeker.id.int % 3)
        for i in range(num_saves):
            job_index = (seeker.id.int + i) % len(jobs)
            saved = create_saved_job(db, jobs[job_index], seeker)
            all_saved.append(saved)
    
    print(f"[SEED] Created {len(all_saved)} saved jobs")
    return all_saved


def seed_events(db: Session, jobs: list, applications: list, users_by_role: dict) -> list:
    """Create 5 monthly events."""
    print("[SEED] Creating test events...")
    
    all_events = []
    
    # Get HR recruiters and company admins who would create events
    event_creators = users_by_role["hr_recruiter"] + users_by_role["company_admin"]
    
    event_data = [
        {"title": "Senior Developer Interview", "type": "interview", "days": 2},
        {"title": "Team Sync Meeting", "type": "meeting", "days": 5},
        {"title": "Job Posting Deadline", "type": "deadline", "days": 7},
        {"title": "Follow-up with Candidate", "type": "follow_up", "days": 10},
        {"title": "Monthly Review Reminder", "type": "reminder", "days": 15},
    ]
    
    for i, data in enumerate(event_data):
        creator = event_creators[i % len(event_creators)]
        related_job = jobs[i] if i < len(jobs) else None
        related_app = applications[i] if i < len(applications) else None
        
        event = create_event(
            db, creator, data["title"], data["type"], 
            data["days"], related_job, related_app
        )
        all_events.append(event)
    
    print(f"[SEED] Created {len(all_events)} test events")
    return all_events


def seed_hello_world(db: Session) -> None:
    """Ensure HelloWorld table has seed marker."""
    existing = db.query(HelloWorld).filter(HelloWorld.message.contains(SEED_MARKER)).first()
    if not existing:
        hello = HelloWorld(message=f"{SEED_MARKER} Database seeded at {datetime.now(timezone.utc).isoformat()}")
        db.add(hello)
        db.commit()


# ── Public API ───────────────────────────────────────────────────────

def seed_all(db: Session) -> dict:
    """
    Run all seed operations. Idempotent — safe to run multiple times.
    Returns summary of created data.
    """
    print("=" * 60)
    print("[SEED] Starting database seed...")
    print("=" * 60)
    
    # Create users
    users_by_role = seed_users(db)
    
    # Create companies
    companies = seed_companies(db, users_by_role)
    
    # Create jobs (10 per company = 30 total)
    jobs = seed_jobs(db, companies, users_by_role)
    
    # Create applications with pipeline data
    applications = seed_applications(db, jobs, users_by_role)
    
    # Create saved jobs
    saved_jobs = seed_saved_jobs(db, jobs, users_by_role)
    
    # Create events
    events = seed_events(db, jobs, applications, users_by_role)
    
    # Mark seed completion
    seed_hello_world(db)
    
    print("=" * 60)
    print("[SEED] Database seed completed successfully!")
    print("=" * 60)
    print(f"\nSeed Summary:")
    print(f"  • Users: {len(TEST_USERS)} (1 SA, 2 CA, 3 HR, 5 JS)")
    print(f"  • Companies: {len(companies)}")
    print(f"  • Jobs: {len(jobs)}")
    print(f"  • Applications: {len(applications)}")
    print(f"  • Saved Jobs: {len(saved_jobs)}")
    print(f"  • Events: {len(events)}")
    print(f"\nAll test accounts use password: {KNOWN_PASSWORD}")
    
    return {
        "users": users_by_role,
        "companies": companies,
        "jobs": jobs,
        "applications": applications,
        "saved_jobs": saved_jobs,
        "events": events,
    }


def clear_seed_data(db: Session) -> None:
    """Clear all seed data from the database."""
    print("[SEED] Clearing seed data...")
    
    # Delete in order to respect foreign keys
    # 1. Events (no dependencies on other seed tables)
    db.query(Event).filter(Event.title.in_([
        "Senior Developer Interview",
        "Team Sync Meeting", 
        "Job Posting Deadline",
        "Follow-up with Candidate",
        "Monthly Review Reminder",
    ])).delete(synchronize_session=False)
    
    # 2. Saved Jobs
    db.query(SavedJob).filter(
        SavedJob.user_id.in_(
            db.query(User.id).filter(User.email.like(f"%@{SEED_EMAIL_DOMAIN}"))
        )
    ).delete(synchronize_session=False)
    
    # 3. Applications
    db.query(Application).filter(
        Application.applicant_id.in_(
            db.query(User.id).filter(User.email.like(f"%@{SEED_EMAIL_DOMAIN}"))
        )
    ).delete(synchronize_session=False)
    
    # 4. Jobs
    db.query(Job).filter(
        Job.company_id.in_(
            db.query(Company.id).filter(Company.slug.in_([c["slug"] for c in TEST_COMPANIES]))
        )
    ).delete(synchronize_session=False)
    
    # 5. Companies
    db.query(Company).filter(Company.slug.in_([c["slug"] for c in TEST_COMPANIES])).delete(synchronize_session=False)
    
    # 6. Users
    db.query(User).filter(User.email.like(f"%@{SEED_EMAIL_DOMAIN}")).delete(synchronize_session=False)
    
    # 7. HelloWorld seed marker
    db.query(HelloWorld).filter(HelloWorld.message.contains(SEED_MARKER)).delete(synchronize_session=False)
    
    db.commit()
    print("[SEED] Seed data cleared successfully")


# ── CLI Entry Points ─────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    db = SessionLocal()
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--reset":
            clear_seed_data(db)
            print("[SEED] Database cleared. Now re-seeding...")
        
        seed_all(db)
        
    except Exception as e:
        print(f"[SEED] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()
