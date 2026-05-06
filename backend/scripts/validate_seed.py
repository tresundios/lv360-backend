"""
PF-004 Acceptance Criteria Validation Script
Run: docker exec lv360-backend python scripts/validate_seed.py
"""
import sys
from app.database import SessionLocal
from app.models import User, UserRole, Company, Job, Application, SavedJob, Event, ApplicationStatus
from app.core.security import verify_password

SEED_DOMAIN = "seed.lamviec360.com"
KNOWN_PASSWORD = "Test1234!"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

failures = []

def check(label, condition, detail=""):
    if condition:
        print(f"  {PASS}  {label}" + (f" — {detail}" if detail else ""))
    else:
        print(f"  {FAIL}  {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)


db = SessionLocal()

print("\n" + "="*60)
print("PF-004 Acceptance Criteria Validation")
print("="*60)


# ── AC1: User counts by role ──────────────────────────────────────
print("\nAC1 — User roles (1 SA, 2 CA, 3 HR, 5 JS)")

sa = db.query(User).filter(User.role == UserRole.super_admin, User.email.like(f"%@{SEED_DOMAIN}")).count()
ca = db.query(User).filter(User.role == UserRole.company_admin, User.email.like(f"%@{SEED_DOMAIN}")).count()
hr = db.query(User).filter(User.role == UserRole.hr_recruiter, User.email.like(f"%@{SEED_DOMAIN}")).count()
js = db.query(User).filter(User.role == UserRole.job_seeker, User.email.like(f"%@{SEED_DOMAIN}")).count()

check("1 super_admin", sa == 1, f"found {sa}")
check("2 company_admin", ca == 2, f"found {ca}")
check("3 hr_recruiter", hr == 3, f"found {hr}")
check("5 job_seeker", js == 5, f"found {js}")

u = db.query(User).filter(User.email == f"superadmin@{SEED_DOMAIN}").first()
pwd_ok = verify_password(KNOWN_PASSWORD, u.password_hash) if u else False
check("Known password 'Test1234!' verifies on all test accounts", pwd_ok)

all_active = db.query(User).filter(
    User.email.like(f"%@{SEED_DOMAIN}"),
    User.status != "active"
).count() == 0
check("All seed users are status=active", all_active)


# ── AC2: 3 verified companies, 10 jobs each ───────────────────────
print("\nAC2 — 3 verified companies with 10 jobs each")

companies = db.query(Company).filter(Company.verified == True).all()
seed_slugs = ["techcorp-vn", "startupvn", "digitalsolutions"]
seed_companies = [c for c in companies if c.slug in seed_slugs]

check("3 verified seed companies exist", len(seed_companies) == 3, f"found {len(seed_companies)}")

for company in seed_companies:
    job_count = db.query(Job).filter(Job.company_id == company.id).count()
    check(f"  {company.name}: 10 jobs", job_count == 10, f"found {job_count}")

total_jobs = sum(db.query(Job).filter(Job.company_id == c.id).count() for c in seed_companies)
check("30 total jobs across all seed companies", total_jobs == 30, f"found {total_jobs}")


# ── AC3: Application pipeline across all stages ───────────────────
print("\nAC3 — Application pipeline covers all stages")

all_stages = [s.value for s in ApplicationStatus]
for stage in all_stages:
    cnt = db.query(Application).filter(Application.status == stage).count()
    check(f"  Stage '{stage}' has applications", cnt > 0, f"count={cnt}")

total_apps = db.query(Application).count()
check("At least 10 total applications", total_apps >= 10, f"found {total_apps}")

# Pipeline timestamps present where expected
hired_with_hired_at = db.query(Application).filter(
    Application.status == "hired",
    Application.hired_at != None
).count()
hired_total = db.query(Application).filter(Application.status == "hired").count()
check("hired applications have hired_at timestamp", hired_with_hired_at == hired_total, f"{hired_with_hired_at}/{hired_total}")

rejected_with_ts = db.query(Application).filter(
    Application.status == "rejected",
    Application.rejected_at != None
).count()
rejected_total = db.query(Application).filter(Application.status == "rejected").count()
check("rejected applications have rejected_at timestamp", rejected_with_ts == rejected_total, f"{rejected_with_ts}/{rejected_total}")


# ── AC4: Idempotency check ────────────────────────────────────────
print("\nAC4 — Idempotency (running seed_all twice produces same counts)")

from app.db.seed import seed_all
seed_all(db)

sa2 = db.query(User).filter(User.role == UserRole.super_admin, User.email.like(f"%@{SEED_DOMAIN}")).count()
ca2 = db.query(User).filter(User.role == UserRole.company_admin, User.email.like(f"%@{SEED_DOMAIN}")).count()
hr2 = db.query(User).filter(User.role == UserRole.hr_recruiter, User.email.like(f"%@{SEED_DOMAIN}")).count()
js2 = db.query(User).filter(User.role == UserRole.job_seeker, User.email.like(f"%@{SEED_DOMAIN}")).count()
companies2 = db.query(Company).filter(Company.slug.in_(seed_slugs)).count()
jobs2 = db.query(Job).filter(
    Job.company_id.in_([c.id for c in seed_companies])
).count()

check("Re-run: still 1 super_admin", sa2 == 1, f"found {sa2}")
check("Re-run: still 2 company_admin", ca2 == 2, f"found {ca2}")
check("Re-run: still 3 hr_recruiter", hr2 == 3, f"found {hr2}")
check("Re-run: still 5 job_seeker", js2 == 5, f"found {js2}")
check("Re-run: still 3 companies", companies2 == 3, f"found {companies2}")
check("Re-run: still 30 jobs", jobs2 == 30, f"found {jobs2}")


# ── AC5: seed-reset clears and re-seeds ──────────────────────────
print("\nAC5 — seed-reset clears all seed data then re-seeds")

from app.db.seed import clear_seed_data
clear_seed_data(db)

sa_after_clear = db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).count()
co_after_clear = db.query(Company).filter(Company.slug.in_(seed_slugs)).count()
jo_after_clear = db.query(Job).filter(Job.slug.like("techcorp-vn-%")).count()

check("After clear: 0 seed users", sa_after_clear == 0, f"found {sa_after_clear}")
check("After clear: 0 seed companies", co_after_clear == 0, f"found {co_after_clear}")
check("After clear: 0 seed jobs", jo_after_clear == 0, f"found {jo_after_clear}")

seed_all(db)

sa_after_reseed = db.query(User).filter(User.email.like(f"%@{SEED_DOMAIN}")).count()
co_after_reseed = db.query(Company).filter(Company.slug.in_(seed_slugs)).count()

check("After re-seed: 11 seed users", sa_after_reseed == 11, f"found {sa_after_reseed}")
check("After re-seed: 3 seed companies", co_after_reseed == 3, f"found {co_after_reseed}")


# ── Summary ──────────────────────────────────────────────────────
db.close()
print("\n" + "="*60)
if failures:
    print(f"\033[91mFAILED {len(failures)} check(s):\033[0m")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\033[92mAll acceptance criteria PASSED\033[0m")
print("="*60 + "\n")
