# US-005 — F2.5 Account Lockout — Postman Collection Guide

**Collection file:** `docs/US-005-Postman-Collection.json`  
**Base URL:** `http://localhost:8000`  
**Seed password:** `Test1234!`  
**PRD reference:** BR-015, AUTH-FR-006

---

## User Story

> As a Super Admin,  
> I want to have the system lock accounts automatically after 3 consecutive failed login attempts,  
> so that brute-force and credential stuffing attacks are blocked without any manual intervention.

---

## Setup

### Import

Postman → **Import** → select `docs/US-005-Postman-Collection.json`

### Pre-requisites

```bash
# Start services
make up

# Run migrations (includes audit_logs table)
make migrate

# Seed test data
make seed
```

### Verify backend is healthy

```bash
curl http://localhost:8000/health
# → {"status":"healthy"}
```

---

## Collection Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `baseUrl` | `http://localhost:8000` | API base URL |
| `accessToken` | *(auto-set)* | JWT access token from successful login |
| `testEmail` | `js.01@seed.lamviec360.com` | Test user for lockout testing |
| `correctPassword` | `Test1234!` | Correct password for test user |
| `wrongPassword` | `WrongPass999!` | Wrong password to trigger failures |

---

## Acceptance Criteria → Test Mapping

| AC | Criterion | Tests | Validation Method |
|----|-----------|-------|-------------------|
| **AC1** | 3 wrong passwords → locked, HTTP 423 on 4th | S03–S08 | 3 × 401, then 423 `ACCOUNT_LOCKED` |
| **AC2** | 2 failures + 1 success → counter reset, NOT locked | S12–S16 | 2 × 401, then 200, then 1 failure + 200 again |
| **AC3** | Locked account visible with `status=locked` filter | S06, S20 | HTTP 423 confirms locked status |
| **AC4** | Unlock only via Super Admin password reset | S09–S11 | Forgot-password → reset → login succeeds |
| **AC5** | Lock event logged to audit log with timestamp | S19 | DB query confirms `audit_logs` entry |

---

## Test Details

### 00 — Setup

| # | Request | Method | Endpoint | Expected |
|---|---------|--------|----------|----------|
| S01 | Health check | `GET` | `/health` | 200 |
| S02 | Baseline login | `POST` | `/api/v1/auth/login` | 200, confirms test user works |

---

### 01 — AC1: Lock after 3 consecutive failures

| # | Request | Method | Endpoint | Expected |
|---|---------|--------|----------|----------|
| S03 | Failed #1 | `POST` | `/api/v1/auth/login` | 401, `INVALID_CREDENTIALS` |
| S04 | Failed #2 | `POST` | `/api/v1/auth/login` | 401, `INVALID_CREDENTIALS` |
| S05 | Failed #3 (triggers lock) | `POST` | `/api/v1/auth/login` | 401, `INVALID_CREDENTIALS` |
| S06 | 4th attempt (correct pw) | `POST` | `/api/v1/auth/login` | **423**, `ACCOUNT_LOCKED` |
| S07 | 5th attempt (wrong pw) | `POST` | `/api/v1/auth/login` | **423**, `ACCOUNT_LOCKED` |
| S08 | Locked (Vietnamese) | `POST` | `/api/v1/auth/login` | **423**, message contains "khóa" |

**Key behavior:**
- Failures 1–3: returns `401 INVALID_CREDENTIALS` (does not reveal lock threshold)
- After lock: returns `423 ACCOUNT_LOCKED` regardless of password correctness
- i18n: Vietnamese and English messages both work

---

### 02 — AC4: Unlock via password reset

| # | Request | Method | Endpoint | Expected |
|---|---------|--------|----------|----------|
| S09 | Forgot password | `POST` | `/api/v1/auth/forgot-password` | 200, `FORGOT_PASSWORD_SENT` |
| S10 | Reset password | `POST` | `/api/v1/auth/reset-password` | 200, `PASSWORD_RESET_SUCCESS` |
| S11 | Login after unlock | `POST` | `/api/v1/auth/login` | 200, token issued |

**How to get the reset token (S09 → S10):**

After running S09, check the backend logs:

```bash
docker compose -f docker-compose.local.yml --env-file .env.local logs backend --tail=5
```

Look for:
```
[RESET] Password reset link for js.01@seed.lamviec360.com: http://localhost:3080/reset-password?token=eyJhbG...
```

Copy the `token=` value and paste it into S10's request body, replacing `PASTE_RESET_TOKEN_FROM_LOGS`.

**What happens on reset:**
- `user.status` changes from `locked` → `active`
- `user.failed_login_count` resets to `0`
- `AuditLog` entry with `action=ACCOUNT_UNLOCKED` is created

---

### 03 — AC2: Counter reset on success

| # | Request | Method | Endpoint | Expected |
|---|---------|--------|----------|----------|
| S12 | Failed #1 | `POST` | `/api/v1/auth/login` | 401 |
| S13 | Failed #2 | `POST` | `/api/v1/auth/login` | 401 |
| S14 | Correct password | `POST` | `/api/v1/auth/login` | **200** (counter reset) |
| S15 | Failed #1 (post-reset) | `POST` | `/api/v1/auth/login` | 401 (not locked!) |
| S16 | Correct password again | `POST` | `/api/v1/auth/login` | **200** (still active) |

**What this validates:**
- 2 failures followed by 1 success does NOT lock the account
- Counter is fully reset to 0 — next lock requires 3 NEW consecutive failures
- S15+S16 confirm: 1 failure after reset does not trigger lock

---

### 04 — AC5: Audit log verification

| # | Request | Method | Endpoint | Expected |
|---|---------|--------|----------|----------|
| S17 | Failed #1 | `POST` | `/api/v1/auth/login` | 401 |
| S18 | Failed #2 | `POST` | `/api/v1/auth/login` | 401 |
| S19 | Failed #3 (triggers lock) | `POST` | `/api/v1/auth/login` | 401 (lock created) |
| S20 | Confirm locked | `POST` | `/api/v1/auth/login` | 423 |

**Verifying the audit log:**

After S19 triggers the lock, query the database:

```bash
docker compose -f docker-compose.local.yml --env-file .env.local exec postgres \
  psql -U postgres -d lv360 -c \
  "SELECT id, user_id, action, detail, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 5;"
```

Expected output:
```
 action          | detail                                                           | created_at
-----------------+------------------------------------------------------------------+----------------------------
 ACCOUNT_LOCKED  | Account locked after 3 consecutive failed login attempts         | 2026-05-21 10:15:30.123+00
```

---

## Flow Diagram

```
Login Request
    │
    ├── User not found? → 401 INVALID_CREDENTIALS
    │
    ├── status == locked? → 423 ACCOUNT_LOCKED
    │
    ├── Wrong password?
    │   ├── failed_login_count += 1
    │   ├── count >= 3? → status = locked + AuditLog(ACCOUNT_LOCKED)
    │   └── → 401 INVALID_CREDENTIALS
    │
    ├── status == suspended? → 403 ACCOUNT_SUSPENDED
    ├── status == pending? → 403 ACCOUNT_PENDING
    │
    └── Correct password
        ├── failed_login_count = 0 (reset)
        └── → 200 + tokens
```

---

## Implementation Reference

| Component | File | Details |
|-----------|------|---------|
| Lockout logic | `services/auth_service.py:181-231` | `MAX_FAILED_LOGIN_ATTEMPTS = 3`, increment + lock + audit |
| Unlock logic | `services/auth_service.py:397-405` | Reset unlocks locked accounts |
| `UserStatus.locked` | `models/user.py:45` | Enum value |
| `AuditLog` model | `models/audit.py` | `user_id`, `action`, `detail`, `ip_address`, `created_at` |
| `ACCOUNT_LOCKED` i18n | `core/i18n.py:37` | vi + en translations |
| Migration | `alembic/versions/2026_05_21_account_lockout.py` | Adds `locked` to enum + `audit_logs` table |

---

## Important Notes

1. **Run order matters** — Sections 01 and 04 lock the test user account. Section 02 unlocks it. Run sequentially.
2. **S10 requires manual token** — Paste the reset token from Docker logs.
3. **Re-running the collection** — If the test user is already locked, run Section 02 first to unlock, or re-seed: `make seed`.
4. **Threshold** — `MAX_FAILED_LOGIN_ATTEMPTS = 3` (configurable in `auth_service.py`).

---

## Running the Collection

### In Postman UI

1. Import `US-005-Postman-Collection.json`
2. Ensure backend is running (`make up && make seed`)
3. Run folders **sequentially** (00 → 01 → 02 → 03 → 04)

### Via Newman CLI

```bash
newman run docs/US-005-Postman-Collection.json --reporters cli --folder "00 — Setup" --folder "01 — AC1: Lock after 3 consecutive failures"
```

> **Note:** Sections 02 and 04 require manual token paste and must be run interactively.

---

## Companion Unit Tests

The collection is complemented by `tests/test_us005_account_lockout.py` (22 tests):

```bash
make test
# or specifically:
docker compose -f docker-compose.local.yml --env-file .env.local exec backend pytest tests/test_us005_account_lockout.py -v
```

| Test Class | AC | Count |
|------------|-----|-------|
| `TestAC1LockAfterThreeFailures` | AC1 | 6 |
| `TestAC2CounterResetOnSuccess` | AC2 | 2 |
| `TestAC3LockedStatus` | AC3 | 3 |
| `TestAC4UnlockViaPasswordReset` | AC4 | 3 |
| `TestAC5AuditLog` | AC5 | 4 |
| `TestConstants` + `TestAccountLockedI18n` | — | 4 |
