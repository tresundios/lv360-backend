# PF-004 Browser Test Guide — Seed Data Validation

**Base URL:** `http://localhost:8000`  
**Swagger UI:** `http://localhost:8000/docs`  
**ReDoc:** `http://localhost:8000/redoc`  
**Password for all seed accounts:** `Test1234!`

> All tests use Swagger UI (`/docs`) unless a `curl` alternative is shown.
> Copy the `access_token` from each login response and click **Authorize** in Swagger to use protected endpoints.

---

## Prerequisites

```bash
make up
make migrate
make seed
```

Confirm backend is healthy:
```
GET http://localhost:8000/health
Expected: { "status": "healthy" }
```

---

## AC1 — User Roles (1 SA, 2 CA, 3 HR, 5 JS)

### T01 — Login as super_admin

```
POST /api/v1/auth/login
{
  "email": "superadmin@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:**
- `200 OK`
- `requires_2fa: false`
- `access_token` present
- `user.role = "super_admin"`
- `user.status = "active"`
- `user.first_login_complete = true`

---

### T02 — Login as company_admin (triggers 2FA)

```
POST /api/v1/auth/login
{
  "email": "ca.techcorp@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:**
- `200 OK`
- `requires_2fa: true`
- `access_token: ""`  ← empty until OTP verified
- `user.role = "company_admin"`

**Then complete 2FA** — get the OTP from backend logs:
```bash
docker logs lv360-backend --tail 20 | grep OTP
```

```
POST /api/v1/auth/login/2fa
{
  "user_id": "<user_id from login response>",
  "otp_code": "<6-digit OTP from logs>"
}
```
**Expected:**
- `200 OK`
- `access_token` present
- `refresh_token` present

---

### T03 — Login as second company_admin

```
POST /api/v1/auth/login
{
  "email": "ca.startupvn@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:** Same 2FA flow as T02. `user.role = "company_admin"`

---

### T04 — Login as hr_recruiter (no 2FA)

```
POST /api/v1/auth/login
{
  "email": "hr.techcorp1@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:**
- `200 OK`
- `requires_2fa: false`
- `user.role = "hr_recruiter"`

Repeat for:
- `hr.techcorp2@seed.lamviec360.com`
- `hr.startupvn@seed.lamviec360.com`

---

### T05 — Login as job_seeker (no 2FA)

```
POST /api/v1/auth/login
{
  "email": "js1@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:**
- `200 OK`
- `requires_2fa: false`
- `user.role = "job_seeker"`
- `user.consent_given = true`

Repeat for: `js2`, `js3`, `js4`, `js5` `@seed.lamviec360.com`

---

### T06 — Verify /me returns correct profile

> Authorize in Swagger with a valid `access_token` from any login above.

```
GET /api/v1/auth/me
```
**Expected:**
- `200 OK`
- `email` matches logged-in user
- `status = "active"`
- `first_login_complete = true`

---

### T07 — Wrong password returns 401

```
POST /api/v1/auth/login
{
  "email": "superadmin@seed.lamviec360.com",
  "password": "WrongPassword"
}
```
**Expected:** `401 Unauthorized`

---

### T08 — Non-seed email returns 401

```
POST /api/v1/auth/login
{
  "email": "notexist@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:** `401 Unauthorized`

---

## AC2 — 3 Verified Companies, 10 Jobs Each

> Use `psql` or TablePlus to verify directly, as job/company list endpoints are not yet exposed.

### T09 — Verify companies in database

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT name, slug, verified FROM companies WHERE slug IN ('techcorp-vn','startupvn','digitalsolutions');"
```
**Expected:** 3 rows, all `verified = t`

---

### T10 — Verify 10 jobs per company

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT c.name, COUNT(j.id) AS job_count FROM companies c JOIN jobs j ON j.company_id = c.id WHERE c.slug IN ('techcorp-vn','startupvn','digitalsolutions') GROUP BY c.name;"
```
**Expected:** 3 rows each showing `job_count = 10`

---

### T11 — Verify jobs are published

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT status, COUNT(*) FROM jobs GROUP BY status;"
```
**Expected:** Only `published` status, count = 30

---

## AC3 — Application Pipeline Across All Stages

### T12 — Verify all 6 stages have applications

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT status, COUNT(*) FROM applications GROUP BY status ORDER BY status;"
```
**Expected:** 6 rows — `new`, `screening`, `interview`, `offer`, `hired`, `rejected` — each with count ≥ 1

---

### T13 — Verify pipeline timestamps

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT status, hired_at IS NOT NULL AS has_hired_at, rejected_at IS NOT NULL AS has_rejected_at FROM applications WHERE status IN ('hired','rejected') LIMIT 10;"
```
**Expected:**
- `hired` rows: `has_hired_at = true`
- `rejected` rows: `has_rejected_at = true`

---

### T14 — Verify saved jobs exist

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT COUNT(*) FROM saved_jobs;"
```
**Expected:** count ≥ 1

---

### T15 — Verify events exist

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT title, event_date FROM events ORDER BY event_date LIMIT 5;"
```
**Expected:** 5 rows with future or near-future `event_date`

---

## AC4 — Idempotency (make seed safe to run multiple times)

### T16 — Run seed twice, counts must not change

```bash
make seed
```
Then immediately run:
```bash
make seed
```

Verify counts are identical:
```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT role, COUNT(*) FROM users WHERE email LIKE '%@seed.lamviec360.com' GROUP BY role ORDER BY role;"
```
**Expected (both runs):**

| role | count |
|------|-------|
| company_admin | 2 |
| hr_recruiter | 3 |
| job_seeker | 5 |
| super_admin | 1 |

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT COUNT(*) FROM companies WHERE slug IN ('techcorp-vn','startupvn','digitalsolutions');"
```
**Expected:** `3` — not 6

```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT COUNT(*) FROM jobs;"
```
**Expected:** `30` — not 60

---

### T17 — Token still valid after re-seed (no session invalidation)

1. Login and save `access_token`
2. Run `make seed` again
3. Call `GET /api/v1/auth/me` with the same token

**Expected:** `200 OK` — user session unaffected

---

## AC5 — make seed-reset Clears and Re-seeds

### T18 — seed-reset wipes all seed data then restores

```bash
make seed-reset
```

Verify users restored:
```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT role, COUNT(*) FROM users WHERE email LIKE '%@seed.lamviec360.com' GROUP BY role;"
```
**Expected:** Same 4 rows as T16 table above

Verify companies restored:
```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT name, verified FROM companies WHERE slug IN ('techcorp-vn','startupvn','digitalsolutions');"
```
**Expected:** 3 rows, all `verified = t`

---

### T19 — Login works after seed-reset

```
POST /api/v1/auth/login
{
  "email": "superadmin@seed.lamviec360.com",
  "password": "Test1234!"
}
```
**Expected:** `200 OK` with `access_token`

---

### T20 — Old tokens invalidated after seed-reset

1. Login before `make seed-reset` → save `access_token`
2. Run `make seed-reset`
3. Call `GET /api/v1/auth/me` with the old token

**Expected:** `401 Unauthorized` — user was deleted and recreated with new UUID

---

## Token Lifecycle Tests

### T21 — Token refresh works

```
POST /api/v1/auth/refresh
{
  "refresh_token": "<refresh_token from login>"
}
```
**Expected:**
- `200 OK`
- New `access_token` and `refresh_token` issued

---

### T22 — Logout revokes refresh token

```
POST /api/v1/auth/logout
{
  "refresh_token": "<refresh_token>"
}
```
**Expected:** `200 OK`

Then attempt to refresh with same token:
```
POST /api/v1/auth/refresh
{
  "refresh_token": "<same refresh_token>"
}
```
**Expected:** `401 Unauthorized`

---

### T23 — Role-based access control

Login as `js1@seed.lamviec360.com` (job_seeker), then attempt invite endpoint:

```
POST /api/v1/auth/invite
Authorization: Bearer <job_seeker_access_token>
{
  "email": "test@example.com",
  "role": "hr_recruiter",
  "company_id": "<any uuid>"
}
```
**Expected:** `403 Forbidden`

Repeat with `superadmin` token:
**Expected:** `201 Created`

---

## Automated Validation (All ACs at once)

```bash
make validate-seed
```
**Expected:** All checks print `PASS`, exit code `0`

---

## Quick Reference — All Seed Accounts

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| super_admin | superadmin@seed.lamviec360.com | Test1234! | No 2FA |
| company_admin | ca.techcorp@seed.lamviec360.com | Test1234! | 2FA required |
| company_admin | ca.startupvn@seed.lamviec360.com | Test1234! | 2FA required |
| hr_recruiter | hr.techcorp1@seed.lamviec360.com | Test1234! | No 2FA |
| hr_recruiter | hr.techcorp2@seed.lamviec360.com | Test1234! | No 2FA |
| hr_recruiter | hr.startupvn@seed.lamviec360.com | Test1234! | No 2FA |
| job_seeker | js1@seed.lamviec360.com | Test1234! | No 2FA, consent=true |
| job_seeker | js2@seed.lamviec360.com | Test1234! | No 2FA, consent=true |
| job_seeker | js3@seed.lamviec360.com | Test1234! | No 2FA, consent=true |
| job_seeker | js4@seed.lamviec360.com | Test1234! | No 2FA, consent=true |
| job_seeker | js5@seed.lamviec360.com | Test1234! | No 2FA, consent=true |



### Useful DB Commands

```bash
# Get company ID (needed for invite tests)
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT id FROM companies LIMIT 1;"

# Count users by role
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT role, COUNT(*) FROM users GROUP BY role;"

# List all seed accounts
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT email, role, status FROM users WHERE email LIKE '%@seed.lamviec360.com' ORDER BY role;"
```

### 2FA note (T04): Before sending, grab the OTP:

```bash
docker logs lv360-backend --tail 10 2>&1 | grep OTP
```
Paste it into the otp_code field in T04 body.

Run entire collection at once: Postman → Run collection → all tests with auto-assertions will execute in sequence.