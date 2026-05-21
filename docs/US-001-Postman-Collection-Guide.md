# US-001 — F2.1 Database Schema — Postman Collection Guide

**Collection file:** `docs/US-001-Postman-Collection.json`  
**Base URL:** `http://localhost:8000`  
**Seed password:** `Test1234!`  
**PRD reference:** AUTH-FR-001 to AUTH-FR-009

---

## User Story

> As a Developer,  
> I want to have all authentication tables created via Alembic migration with correct constraints, indexes, and FK relationships,  
> so that the platform has a secure, normalised data foundation for all authentication operations.

---

## Setup

### Import

Postman → **Import** → select `docs/US-001-Postman-Collection.json`

### Pre-requisites

```bash
# Start services
make up

# Run migrations (creates all 4 auth tables)
make migrate

# Seed test data
make seed

# Get companyId for invite tests (set as collection variable)
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT id FROM companies LIMIT 1;"
```

### Collection Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `baseUrl` | `http://localhost:8000` | API base URL |
| `accessToken` | *(auto-set)* | JWT access token |
| `refreshToken` | *(auto-set)* | JWT refresh token |
| `userId` | *(auto-set)* | Current user UUID |
| `caUserId` | *(auto-set)* | Company admin UUID |
| `companyId` | *(manual)* | Set before S12 — get from DB query above |
| `newUserId` | *(auto-set)* | Registered user UUID |
| `inviteToken` | *(auto-set)* | JWT invite token, saved from S12 response |

---

## Acceptance Criteria → Test Mapping

| AC | Criterion | Tests | Validation Method |
|----|-----------|-------|-------------------|
| **AC1** | `make migrate` creates all 4 tables without error | S01 | Health check passes → migration ran on startup |
| **AC2** | `users` table: id (UUID PK), email (UNIQUE), password_hash (nullable), role (enum), status (enum), first_login_complete, consent_given, consent_timestamp, failed_login_count | S02–S06 | Login/me/register exercises all columns; tests assert types |
| **AC3** | `refresh_tokens`: id, user_id (FK CASCADE), token_hash, expires_at, revoked | S07–S10 | Token issue → refresh → logout → revoked refresh |
| **AC4** | `team_invitations`: id, company_id, email, role, token_hash, expires_at (72h), accepted, revoked | S11–S13 | Create invite → view invite → assert expires_at ~72h |
| **AC5** | `social_accounts`: UNIQUE(provider, provider_user_id) | S14–S15 | OAuth routes registered (table scaffolded) |
| **AC6** | Migration reversible via `make migrate-down` | S16 + manual | Downgrade → upgrade → health check passes |

---

## Folder Structure & Requests

### 1. 00 — Health & Migration

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S01 | Health Check | `GET` | `/health` | None | 200, `status: "healthy"` |

---

### 2. AC2 — users table

Validates all required columns via API responses.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S02 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200, validates: `id` (UUID), `email`, `role` (enum), `status` (enum), `first_login_complete` (bool) |
| S03 | GET /me | `GET` | `/api/v1/auth/me` | Bearer | 200, validates all UserOut fields: id, email, full_name, role, account_type, status, first_login_complete, created_at |
| S04 | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200, validates `account_type`, `consent_given` column exists |
| S05 | Wrong password | `POST` | `/api/v1/auth/login` | None | 401, validates `password_hash` column used for comparison |
| S06 | Duplicate email | `POST` | `/api/v1/auth/register/step2` | None | 409, validates `email UNIQUE` constraint |

**Columns covered:**

| Column | Test | How |
|--------|------|-----|
| `id` (UUID PK) | S02, S03 | UUID regex assertion |
| `email` (UNIQUE) | S02, S06 | Login + duplicate 409 |
| `password_hash` (nullable) | S05 | Wrong password → 401 |
| `full_name` | S03 | /me response |
| `role` (enum) | S02, S04 | Enum value assertion |
| `account_type` (enum) | S04 | job_seeker login |
| `status` (enum) | S02 | Enum value assertion |
| `first_login_complete` | S02 | Boolean assertion |
| `consent_given` | S04 | job_seeker has consent |
| `consent_timestamp` | — | DB query (see below) |
| `failed_login_count` | — | DB query (see below) |
| `created_at` | S03 | Timestamp assertion |

---

### 3. AC3 — refresh_tokens table

Validates token lifecycle (issue → refresh → revoke → reject).

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S07 | Login (issue token) | `POST` | `/api/v1/auth/login` | None | 200, `refresh_token` issued |
| S08 | Refresh token | `POST` | `/api/v1/auth/refresh` | None | 200, new tokens (validates `token_hash` lookup + `expires_at` check) |
| S09 | Logout | `POST` | `/api/v1/auth/logout` | None | 200, `LOGOUT_SUCCESS` (sets `revoked=true`) |
| S10 | Refresh after logout | `POST` | `/api/v1/auth/refresh` | None | 401, `SESSION_INVALIDATED` (validates `revoked=true` blocks) |

**Columns covered:**

| Column | Test | How |
|--------|------|-----|
| `id` (UUID PK) | S07 | Row created on login |
| `user_id` (FK CASCADE) | S07 | Token linked to user |
| `token_hash` | S08 | Refresh succeeds (hash matched) |
| `expires_at` | S08 | Refresh succeeds (not expired) |
| `revoked` | S09, S10 | Logout sets true; refresh rejected |

---

### 4. AC4 — team_invitations table

Validates invite creation, viewing, and expiry.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S11 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200, saves token |
| S12 | Create invitation | `POST` | `/api/v1/auth/invite` | Bearer (SA) | 201, `INVITE_SENT`, `invitation_id` UUID, `invite_token` auto-saved |
| S13 | View invitation | `GET` | `/api/v1/auth/invite/{token}` | None | 200, validates: id, email, role, company_id, expires_at (~72h), accepted=false |

**Setup for S12:** Set `companyId` collection variable first.  
**S12 → S13 flow:** S12's test script auto-saves `invite_token` from the response into `{{inviteToken}}`. S13 uses it automatically — no manual log lookup needed.

**Columns covered:**

| Column | Test | How |
|--------|------|-----|
| `id` (UUID PK) | S12 | `invitation_id` in response |
| `company_id` | S13 | UUID in response |
| `email` | S13 | Matches input |
| `role` (enum) | S13 | `hr_recruiter` |
| `token_hash` | S12, S13 | JWT token validated server-side |
| `expires_at` | S13 | Asserts 70–73 hours from now |
| `accepted` | S13 | `false` |
| `revoked` | — | DB query |

---

### 5. AC5 — social_accounts table

Validates table exists with UNIQUE constraint. OAuth not yet implemented.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S14 | Google OAuth placeholder | `GET` | `/api/v1/auth/google/login` | None | 307 or 501 |
| S15 | Zalo OAuth placeholder | `GET` | `/api/v1/auth/zalo/login` | None | 307 or 501 |

**Full DB validation:**
```bash
# Verify table exists with correct constraint
docker exec lv360-postgres psql -U postgres -d lv360 -c "\d social_accounts"

# Verify UNIQUE constraint
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT conname FROM pg_constraint WHERE conrelid = 'social_accounts'::regclass AND contype = 'u';"
# Expected: uq_social_provider_user

# Verify CHECK constraint
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT conname FROM pg_constraint WHERE conrelid = 'social_accounts'::regclass AND contype = 'c';"
# Expected: ck_social_provider
```

---

### 6. AC6 — Migration Reversibility

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S16 | Health after re-migration | `GET` | `/health` | None | 200, `healthy` |

**Manual steps (run before S16):**
```bash
# Downgrade last migration
make migrate-down
# Expected: Running downgrade c3d4e5f6a7b8 -> b2c3d4e5f6a7

# Verify failed_login_count is gone
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='failed_login_count';"
# Expected: (0 rows)

# Upgrade back to head
make migrate
# Expected: Running upgrade b2c3d4e5f6a7 -> c3d4e5f6a7b8

# Verify column restored
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='failed_login_count';"
# Expected: failed_login_count

# Run S16 in Postman
```

---

### 7. FK CASCADE DELETE

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S17 | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200 |
| S18 | AI abuse x4 | `POST` | `/api/v1/auth/ai-abuse` | Bearer | 200 or 401 (session terminated) |
| S19 | Refresh after revoke | `POST` | `/api/v1/auth/refresh` | None | 401, all tokens revoked |

**Full CASCADE verification (DB):**
```bash
# Count tokens for a user before delete
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT COUNT(*) FROM refresh_tokens WHERE user_id = (SELECT id FROM users WHERE email = 'js.05@seed.lamviec360.com');"

# Verify CASCADE is configured
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT confdeltype FROM pg_constraint WHERE conname = 'refresh_tokens_user_id_fkey';"
# Expected: a (CASCADE)

docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT confdeltype FROM pg_constraint WHERE conname = 'social_accounts_user_id_fkey';"
# Expected: a (CASCADE)
```

---

### 8. Index Performance

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S20 | Login (email index) | `POST` | `/api/v1/auth/login` | None | 200, response < 500ms |

**Full index verification (DB):**
```bash
# List all indexes on auth tables
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT tablename, indexname FROM pg_indexes WHERE tablename IN ('users','refresh_tokens','team_invitations','social_accounts') ORDER BY tablename, indexname;"
```

**Expected indexes:**

| Table | Index | Column(s) |
|-------|-------|-----------|
| `users` | `users_pkey` | `id` (PK) |
| `users` | `ix_users_email` | `email` (UNIQUE) |
| `refresh_tokens` | `refresh_tokens_pkey` | `id` (PK) |
| `refresh_tokens` | `ix_refresh_tokens_user_id` | `user_id` (FK) |
| `refresh_tokens` | `ix_refresh_tokens_expires_at` | `expires_at` |
| `team_invitations` | `team_invitations_pkey` | `id` (PK) |
| `team_invitations` | `ix_team_invitations_expires_at` | `expires_at` |
| `social_accounts` | `social_accounts_pkey` | `id` (PK) |
| `social_accounts` | `ix_social_accounts_user_id` | `user_id` (FK) |
| `social_accounts` | `uq_social_provider_user` | `(provider, provider_user_id)` UNIQUE |

---

## Execution Order

1. **S01** — Health check (confirms migration ran)
2. **S02–S06** — AC2: users table columns
3. **S07–S10** — AC3: refresh_tokens table
4. **S11–S13** — AC4: team_invitations table (set `companyId` + `inviteToken` first)
5. **S14–S15** — AC5: social_accounts table (OAuth placeholders)
6. **Manual** — `make migrate-down` + `make migrate` → then **S16** (AC6)
7. **S17–S19** — FK CASCADE DELETE validation
8. **S20** — Index performance check
9. **DB queries** — Run supplementary SQL commands for full column/index coverage

---

## Supplementary DB Validation Commands

These SQL queries provide full coverage for columns not directly exposed via API:

```bash
# AC2: Verify ALL users table columns
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT column_name, data_type, is_nullable, column_default
   FROM information_schema.columns
   WHERE table_name = 'users'
   ORDER BY ordinal_position;"

# AC2: Verify failed_login_count exists and defaults to 0
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT failed_login_count FROM users LIMIT 3;"

# AC2: Verify consent_timestamp is nullable
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT consent_given, consent_timestamp FROM users WHERE role = 'job_seeker' LIMIT 2;"

# AC3: Verify refresh_tokens structure
docker exec lv360-postgres psql -U postgres -d lv360 -c "\d refresh_tokens"

# AC4: Verify team_invitations structure
docker exec lv360-postgres psql -U postgres -d lv360 -c "\d team_invitations"

# AC5: Verify social_accounts structure + constraints
docker exec lv360-postgres psql -U postgres -d lv360 -c "\d social_accounts"

# All tables exist
docker exec lv360-postgres psql -U postgres -d lv360 -c \
  "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('users','refresh_tokens','team_invitations','social_accounts') ORDER BY tablename;"
```

---

## Alembic Migrations

| Revision | File | Changes |
|----------|------|---------|
| `a1b2c3d4e5f6` | `2026_04_11_auth_tables.py` | Creates all 4 tables + enums |
| `b2c3d4e5f6a7` | `2026_05_05_company_job_tables.py` | Company/Job tables |
| `c3d4e5f6a7b8` | `2026_05_21_add_failed_login_count_and_indexes.py` | Adds `failed_login_count`, `ix_refresh_tokens_expires_at`, `ix_team_invitations_expires_at` |

---

## Related Docs

- `docs/PF-004-Postman-Collection-Guide.md` — Full auth API testing guide
- `docs/PF-004-Postman-Collection.json` — Auth API Postman collection
- `docs/i18n-usage-guide.md` — i18n message codes reference
- `docs/deploy-dev-guide.md` — Dev environment setup
