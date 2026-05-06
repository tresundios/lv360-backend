# how to run seed in the dev environment manually

The container is lv360_backend_dev and confirmed healthy. Run:


```bash
ssh deploy@103.175.146.37 "docker exec lv360_backend_dev python -m app.db.seed"
```

```
[DB] Connecting to postgres:5432/lv360
============================================================
[SEED] Starting database seed...
============================================================
[SEED] Creating test users...
  ✓ superadmin@seed.lamviec360.com (super_admin)
  ✓ ca.techcorp@seed.lamviec360.com (company_admin)
  ✓ ca.startupvn@seed.lamviec360.com (company_admin)
  ✓ hr.techcorp1@seed.lamviec360.com (hr_recruiter)
  ✓ hr.techcorp2@seed.lamviec360.com (hr_recruiter)
  ✓ hr.startupvn@seed.lamviec360.com (hr_recruiter)
  ✓ js.01@seed.lamviec360.com (job_seeker)
  ✓ js.02@seed.lamviec360.com (job_seeker)
  ✓ js.03@seed.lamviec360.com (job_seeker)
  ✓ js.04@seed.lamviec360.com (job_seeker)
  ✓ js.05@seed.lamviec360.com (job_seeker)
[SEED] Created 11 test users
[SEED] Creating test companies...
  ✓ TechCorp Vietnam (owner: Nguyen Van A - TechCorp Admin)
  ✓ StartupVN (owner: Tran Thi B - StartupVN Admin)
  ✓ Digital Solutions Ltd (owner: Nguyen Van A - TechCorp Admin)
[SEED] Created 3 test companies
[SEED] Creating test jobs...
[SEED] Created 30 test jobs
[SEED] Creating test applications...
[SEED] Created 31 test applications
[SEED] Creating saved jobs...
[SEED] Created 18 saved jobs
[SEED] Creating test events...
[SEED] Created 5 test events
============================================================
[SEED] Database seed completed successfully!
============================================================
```

Seed Summary:
  • Users: 11 (1 SA, 2 CA, 3 HR, 5 JS)
  • Companies: 3
  • Jobs: 30
  • Applications: 31
  • Saved Jobs: 18
  • Events: 5

All test accounts use password: Test1234!


Using legacy terminal
Configure
Seed ran successfully on dev. All 5 acceptance criteria are now seeded:

✅ 11 users — 1 SA, 2 CA, 3 HR, 5 JS
✅ 3 companies — TechCorp Vietnam, StartupVN, Digital Solutions Ltd
✅ 30 jobs — 10 per company
✅ 31 applications — covering all pipeline stages
✅ 18 saved jobs, 5 events
For future reference — manual seed commands on dev:

```bash
# Seed (idempotent — safe to run multiple times)
ssh deploy@103.175.146.37 "docker exec lv360_backend_dev python -m app.db.seed"
 
# Reset and re-seed cleanly
ssh deploy@103.175.146.37 "docker exec lv360_backend_dev python -m app.db.seed --reset"
```

You can now run the Postman collection against https://dev.lamviec360.com.