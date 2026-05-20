# PF-004 Postman Collection — API Documentation

**Collection file:** `docs/PF-004-Postman-Collection.json`  
**Base URL:** `http://localhost:8000`  
**All seed accounts password:** `Test1234!`  
**i18n:** All responses include `code` + `message`. Set `Accept-Language: en` for English, default is Vietnamese.

---

## Setup

### Import
Postman → **Import** → select `docs/PF-004-Postman-Collection.json`

### Collection Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `baseUrl` | `http://localhost:8000` | API base URL |
| `accessToken` | *(auto-set)* | JWT access token, saved on login |
| `refreshToken` | *(auto-set)* | JWT refresh token, saved on login |
| `userId` | *(auto-set)* | Current user UUID |
| `caUserId` | *(auto-set)* | Company admin user UUID (for 2FA flow) |
| `companyId` | *(manual)* | Set before invite tests — get from DB |
| `newUserId` | *(auto-set)* | Registered user UUID |
| `invitationId` | *(auto-set)* | Created invitation UUID |

### Pre-requisites

```bash
# Start backend
make up

# Run seed (idempotent)
make seed

# Get companyId for invite tests
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT id FROM companies LIMIT 1;"
```

### Authentication
Collection-level auth is **Bearer Token** using `{{accessToken}}`. Login requests auto-save the token.

### Language (i18n)

All API responses now return `code` + localized `message`. Control language via header:

| Header | Language |
|--------|----------|
| `Accept-Language: en` | English |
| `Accept-Language: vi` | Vietnamese |
| *(no header)* | Vietnamese (default) |

**Response format (success):**
```json
{"code": "LOGOUT_SUCCESS", "message": "Logged out successfully."}
```

**Response format (error):**
```json
{"detail": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}}
```

See `docs/i18n-usage-guide.md` for full message codes reference.

---

## Folder Structure

### 1. 00 — Health & Infra

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| — | Health Check | `GET` | `/health` | None | 200, `status: "healthy"` |
| — | Root | `GET` | `/` | None | 200 |

---

### 2. AC1 — User Roles

Login tests for all 11 seed accounts. Validates role, status, 2FA behavior.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| T01 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200, `requires_2fa: false`, token issued |
| T02 | GET /me as super_admin | `GET` | `/api/v1/auth/me` | Bearer | 200, `role: super_admin` |
| T03 | Login company_admin (2FA) | `POST` | `/api/v1/auth/login` | None | 200, `requires_2fa: true`, no token |
| T04 | Complete 2FA | `POST` | `/api/v1/auth/login/2fa` | None | 200, token issued |
| T05 | Login 2nd company_admin | `POST` | `/api/v1/auth/login` | None | 200, `requires_2fa: true` |
| T06 | Login hr_recruiter 1 | `POST` | `/api/v1/auth/login` | None | 200, `role: hr_recruiter` |
| T07 | Login hr_recruiter 2 | `POST` | `/api/v1/auth/login` | None | 200, `role: hr_recruiter` |
| T08 | Login hr_recruiter 3 | `POST` | `/api/v1/auth/login` | None | 200, `role: hr_recruiter` |
| T09 | Login job_seeker 1 | `POST` | `/api/v1/auth/login` | None | 200, `role: job_seeker`, `consent_given: true` |
| T10 | Login job_seeker 2 | `POST` | `/api/v1/auth/login` | None | 200, `role: job_seeker` |
| T11 | Login job_seeker 3 | `POST` | `/api/v1/auth/login` | None | 200 |
| T12 | Login job_seeker 4 | `POST` | `/api/v1/auth/login` | None | 200 |
| T13 | Login job_seeker 5 | `POST` | `/api/v1/auth/login` | None | 200 |
| T14 | Wrong password | `POST` | `/api/v1/auth/login` | None | 401, `code: INVALID_CREDENTIALS` |
| T15 | Non-existent email | `POST` | `/api/v1/auth/login` | None | 401, `code: INVALID_CREDENTIALS` |

**2FA Note (T04):** After sending T03, grab OTP from logs:
```bash
docker logs lv360-backend --tail 10 2>&1 | grep OTP
```

---

### 3. AC4 — Idempotency

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| T16 | Login after 2nd seed run | `POST` | `/api/v1/auth/login` | None | 200, token issued (no duplicates) |

**Pre-step:** Run `make seed` a second time before executing.

---

### 4. Token Lifecycle

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| T17 | Refresh token | `POST` | `/api/v1/auth/refresh` | None | 200, new tokens issued |
| T18 | Logout | `POST` | `/api/v1/auth/logout` | None | 200 |
| T19 | Refresh after logout | `POST` | `/api/v1/auth/refresh` | None | 401, `code: SESSION_INVALIDATED` |
| T20 | /me with no token | `GET` | `/api/v1/auth/me` | None | 401 |

---

### 5. RBAC — Role Enforcement

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| T21 | job_seeker creates invite | `POST` | `/api/v1/auth/invite` | Bearer (JS) | 403 |
| T22 | hr_recruiter creates invite | `POST` | `/api/v1/auth/invite` | Bearer (HR) | 403 |
| T23 | OTP resend — missing user | `POST` | `/api/v1/auth/otp/resend` | None | 404 |

---

### 6. AC5 — seed-reset Recovery

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| T24 | Login after seed-reset | `POST` | `/api/v1/auth/login` | None | 200, `role: super_admin` |
| T25 | job_seeker restored | `POST` | `/api/v1/auth/login` | None | 200, `role: job_seeker` |

**Pre-step:** Run `make seed-reset` before executing.

---

### 7. Protected — GET /me (per role)

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| P01 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200, saves token |
| P02 | GET /me — super_admin | `GET` | `/api/v1/auth/me` | Bearer | 200, full profile fields |
| P03 | Login hr_recruiter | `POST` | `/api/v1/auth/login` | None | 200, saves token |
| P04 | GET /me — hr_recruiter | `GET` | `/api/v1/auth/me` | Bearer | 200, `account_type: employer` |
| P05 | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200, saves token |
| P06 | GET /me — job_seeker | `GET` | `/api/v1/auth/me` | Bearer | 200, `account_type: job_seeker` |
| P07 | /me — no token | `GET` | `/api/v1/auth/me` | None | 401 |
| P08 | /me — invalid token | `GET` | `/api/v1/auth/me` | Invalid JWT | 401, `code: SESSION_INVALIDATED` |

---

### 8. Logout — Per Role

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| L01 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200, saves tokens |
| L02 | Logout super_admin | `POST` | `/api/v1/auth/logout` | Bearer | 200, `code: LOGOUT_SUCCESS` |
| L03 | Refresh after SA logout | `POST` | `/api/v1/auth/refresh` | None | 401 (revoked) |
| L04 | /me after SA logout | `GET` | `/api/v1/auth/me` | Bearer | 200 (JWT still valid until expiry) |
| L05 | Login hr_recruiter | `POST` | `/api/v1/auth/login` | None | 200, saves tokens |
| L06 | Logout hr_recruiter | `POST` | `/api/v1/auth/logout` | Bearer | 200, `code: LOGOUT_SUCCESS` |
| L07 | Refresh after HR logout | `POST` | `/api/v1/auth/refresh` | None | 401 (revoked) |
| L08 | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200, saves tokens |
| L09 | Logout job_seeker | `POST` | `/api/v1/auth/logout` | Bearer | 200, `code: LOGOUT_SUCCESS` |
| L10 | Refresh after JS logout | `POST` | `/api/v1/auth/refresh` | None | 401 (revoked) |
| L11 | Invalid refresh_token | `POST` | `/api/v1/auth/logout` | None | 200 (no info leak) |
| L12 | Double logout | `POST` | `/api/v1/auth/logout` | None | 200 (idempotent) |

---

### 9. Protected — POST /first-login-complete

AUTH-FR-008: Mark onboarding as complete.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| P09 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200 |
| P10 | first-login-complete | `POST` | `/api/v1/auth/first-login-complete` | Bearer | 200, `code: ONBOARDING_COMPLETE` |
| P11 | No token | `POST` | `/api/v1/auth/first-login-complete` | None | 401 |
| P12 | As job_seeker | `POST` | `/api/v1/auth/first-login-complete` | Bearer (JS) | 200 |

---

### 10. Protected — POST /ai-abuse

BR-006: AI abuse tracking. Session terminated after 3+ strikes.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| P13 | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200 |
| P14 | 1st strike | `POST` | `/api/v1/auth/ai-abuse` | Bearer | 200, `count: 1`, `terminated: false` |
| P15 | 2nd strike | `POST` | `/api/v1/auth/ai-abuse` | Bearer | 200, `count: 2`, `terminated: false` |
| P16 | 3rd strike | `POST` | `/api/v1/auth/ai-abuse` | Bearer | 200, `count: 3`, `terminated: false` |
| P17 | 4th strike | `POST` | `/api/v1/auth/ai-abuse` | Bearer | 401, `code: SESSION_TERMINATED` |
| P18 | Refresh after termination | `POST` | `/api/v1/auth/refresh` | None | 401 (all tokens revoked) |
| P19 | No token | `POST` | `/api/v1/auth/ai-abuse` | None | 401 |

---

### 11. Protected — Team Invite (full flow)

AUTH-FR-007: Only `super_admin` and `company_admin` can create invites.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| P20 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200 |
| P21 | Create invite | `POST` | `/api/v1/auth/invite` | Bearer (SA) | 201, `code: INVITE_SENT` |
| P22a | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200, saves token |
| P22b | job_seeker creates invite | `POST` | `/api/v1/auth/invite` | Bearer (JS) | 403 |
| P23a | Login hr_recruiter | `POST` | `/api/v1/auth/login` | None | 200, saves token |
| P23b | hr_recruiter creates invite | `POST` | `/api/v1/auth/invite` | Bearer (HR) | 403 |
| P24 | No token | `POST` | `/api/v1/auth/invite` | None | 401 |
| P25 | View invite | `GET` | `/api/v1/auth/invite/{token}` | None | 200, invite details |
| P26 | Accept invite | `POST` | `/api/v1/auth/invite/accept` | None | 200, tokens + user |

**Setup:** Set `companyId` variable before running P21:
```bash
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT id FROM companies LIMIT 1;"
```

---

### 12. Public — Registration Flow

AUTH-FR-001: Register → OTP → Verify.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| P27 | Register job_seeker | `POST` | `/api/v1/auth/register/step2` | None | 201, `code: OTP_SENT` |
| P28 | Register employer | `POST` | `/api/v1/auth/register/step2` | None | 201, `user_id` |
| P29 | Duplicate email | `POST` | `/api/v1/auth/register/step2` | None | 409, `code: EMAIL_TAKEN` |
| P30 | Verify OTP | `POST` | `/api/v1/auth/register/verify` | None | 200, tokens issued |
| P31 | Resend OTP | `POST` | `/api/v1/auth/otp/resend` | None | 200, `remaining_attempts` |
| P32 | Resend — unknown user | `POST` | `/api/v1/auth/otp/resend` | None | 404 |

---

### 13. Public — Password Reset Flow

AUTH-FR-004: Forgot → Reset.

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| P33 | Forgot password (existing) | `POST` | `/api/v1/auth/forgot-password` | None | 200, `code: FORGOT_PASSWORD_SENT` |
| P34 | Forgot (non-existent) | `POST` | `/api/v1/auth/forgot-password` | None | 200, `code: FORGOT_PASSWORD_SENT` (no info leak) |
| P35 | Reset password | `POST` | `/api/v1/auth/reset-password` | None | 200, `code: PASSWORD_RESET_SUCCESS` |
| P36 | Invalid reset token | `POST` | `/api/v1/auth/reset-password` | None | 400, `code: RESET_LINK_INVALID` |

---

## Execution Order (Recommended)

1. **Health** → confirm server up
2. **AC1** → login all roles (T01–T15)
3. **Protected — GET /me** → P01–P08
4. **Logout — Per Role** → L01–L12
5. **Token Lifecycle** → T17–T20
6. **RBAC** → T21–T23
7. **Protected — first-login-complete** → P09–P12
8. **Protected — ai-abuse** → P13–P19
9. **Protected — Team Invite** → P20–P26
10. **Registration Flow** → P27–P32
11. **Password Reset** → P33–P36
12. **AC4 Idempotency** → run `make seed` again, then T16
13. **AC5 seed-reset** → run `make seed-reset`, then T24–T25

---

## Seed Accounts Quick Reference

| Role | Email | 2FA |
|------|-------|-----|
| super_admin | `superadmin@seed.lamviec360.com` | No |
| company_admin | `ca.techcorp@seed.lamviec360.com` | Yes |
| company_admin | `ca.startupvn@seed.lamviec360.com` | Yes |
| hr_recruiter | `hr.techcorp1@seed.lamviec360.com` | No |
| hr_recruiter | `hr.techcorp2@seed.lamviec360.com` | No |
| hr_recruiter | `hr.startupvn@seed.lamviec360.com` | No |
| job_seeker | `js.01@seed.lamviec360.com` | No |
| job_seeker | `js.02@seed.lamviec360.com` | No |
| job_seeker | `js.03@seed.lamviec360.com` | No |
| job_seeker | `js.04@seed.lamviec360.com` | No |
| job_seeker | `js.05@seed.lamviec360.com` | No |

---

## Useful Commands

```bash
# Get company ID
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT id FROM companies LIMIT 1;"

# Count users by role
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT role, COUNT(*) FROM users GROUP BY role;"

# Check application pipeline
docker exec lv360-postgres psql -U postgres -d lv360 -c "SELECT status, COUNT(*) FROM applications GROUP BY status ORDER BY status;"

# Get OTP from logs (after login/register)
docker logs lv360-backend --tail 10 2>&1 | grep OTP

# Get invite token from logs (after P21)
docker logs lv360-backend --tail 20 2>&1 | grep INVITE

# Get reset token from logs (after P33)
docker logs lv360-backend --tail 10 2>&1 | grep RESET

# Seed (idempotent)
make seed

# Reset and re-seed
make seed-reset
```

---

## Related Docs

- `docs/i18n-usage-guide.md` — Full i18n reference (message codes, frontend integration, adding languages)
- `docs/pf004-browser-test-guide.md` — Manual browser testing guide
- `docs/deploy-dev-guide.md` — Dev environment deployment
