# US-002 — F2.2 Security Utilities — Postman Collection Guide

**Collection file:** `docs/US-002-Postman-Collection.json`  
**Base URL:** `http://localhost:8000`  
**Seed password:** `Test1234!`  
**PRD reference:** AUTH-FR-006, AUTH-FR-009

---

## User Story

> As a Developer,  
> I want to have centralised JWT and password hashing utilities used consistently across all auth endpoints,  
> so that there is no duplication of security logic and all tokens are created and verified through a single trusted module.

---

## Setup

### Import

Postman → **Import** → select `docs/US-002-Postman-Collection.json`

### Pre-requisites

```bash
# Start services
make up

# Run migrations
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
| `accessToken` | *(auto-set)* | JWT access token, saved from login |
| `refreshToken` | *(auto-set)* | Opaque refresh token, saved from login |
| `userId` | *(auto-set)* | Current user UUID |

All variables are **auto-populated** by test scripts — no manual setup required.

---

## Acceptance Criteria → Test Mapping

| AC | Criterion | Tests | Validation Method |
|----|-----------|-------|-------------------|
| **AC1** | `create_access_token(user_id, role)` returns signed JWT with correct claims and expiry | S02–S04 | Decode JWT payload in Postman tests, assert `sub`, `role`, `type=access`, `iat`, `exp`, expiry ≈ 60 min |
| **AC2** | `verify_token()` raises `TokenExpiredException` for expired, `InvalidTokenException` for tampered | S05–S08 | Send tampered/garbage/wrong-secret JWTs → assert 401 + `SESSION_INVALIDATED` |
| **AC3** | `hash_password()` uses argon2 with unique salt each call | S09, S12, S13 | Login correct → 200; case mismatch → 401; two logins → different tokens (different iat) |
| **AC4** | `verify_password(plain, hash)` returns True only for correct password | S09–S12 | Correct → 200; wrong → 401; empty → 401/422; case flip → 401 |
| **AC5** | `JWT_EXPIRY_MINUTES` and `JWT_REFRESH_DAYS` env vars control lifetimes | S02, S14–S18 | Token expiry delta check; refresh token lifecycle (issue → rotate → revoke → reject) |

---

## Test Details

### 00 — Health

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S01 | Health check | `GET` | `/health` | None | 200, `status: healthy` |

---

### 01 — AC1: create_access_token (JWT claims + expiry)

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S02 | Login super_admin | `POST` | `/api/v1/auth/login` | None | 200, JWT with `sub`, `role=super_admin`, `type=access`, `iat`, `exp`. Expiry ≈ 60 min. Saves tokens. |
| S03 | Login job_seeker | `POST` | `/api/v1/auth/login` | None | 200, JWT `role=job_seeker` |
| S04 | Access /me with valid JWT | `GET` | `/api/v1/auth/me` | Bearer | 200, user profile matches `userId` |

**What S02 validates:**
- JWT is a 3-part Base64 string (header.payload.signature)
- Payload contains `sub` (UUID format), `role`, `type=access`, `iat`, `exp`
- `exp - iat ≈ 60 minutes` (default `JWT_EXPIRY_MINUTES`)

---

### 02 — AC2: Token expired vs tampered (distinct errors)

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S05 | Tampered JWT | `GET` | `/api/v1/auth/me` | Bearer (tampered) | 401, `SESSION_INVALIDATED` |
| S06 | Garbage token | `GET` | `/api/v1/auth/me` | Bearer (garbage) | 401, `SESSION_INVALIDATED` |
| S07 | No token | `GET` | `/api/v1/auth/me` | None | 401, `SESSION_INVALIDATED` |
| S08 | Wrong-secret JWT | `GET` | `/api/v1/auth/me` | Bearer (wrong secret) | 401, `SESSION_INVALIDATED` |

**Distinction in backend:**
- **Expired tokens** → `TokenExpiredException` → HTTP 401 + `TOKEN_EXPIRED`
- **Tampered/invalid tokens** → `InvalidTokenException` → HTTP 401 + `SESSION_INVALIDATED`

> **Note:** S05-S08 test tampered/invalid scenarios. Expired token testing is covered by unit tests since creating an already-expired JWT requires server-side code.

---

### 03 — AC3+AC4: Password hashing (argon2, correct/wrong)

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S09 | Correct password | `POST` | `/api/v1/auth/login` | None | 200, token issued |
| S10 | Wrong password | `POST` | `/api/v1/auth/login` | None | 401, `INVALID_CREDENTIALS` |
| S11 | Empty password | `POST` | `/api/v1/auth/login` | None | 401 or 422 |
| S12 | Case-sensitive mismatch | `POST` | `/api/v1/auth/login` | None | 401, `INVALID_CREDENTIALS` |
| S13 | Two logins → different tokens | `POST` | `/api/v1/auth/login` | None | 200, new token ≠ previous |

**AC3 validated:**
- argon2 produces unique salt per call → same password + same user = different hash each time
- Postman can't inspect the hash directly, but S13 shows each login produces a unique JWT (different `iat`)
- Unit tests (`test_us002_security.py::TestAC3HashPassword`) verify argon2 prefix and unique salts

**AC4 validated:**
- S09: correct → True (token issued)
- S10: wrong → False (401)
- S11: empty → False
- S12: case mismatch → False (password is case-sensitive)

---

### 04 — AC5: Refresh token lifecycle (JWT_REFRESH_DAYS)

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S14 | Login → refresh token issued | `POST` | `/api/v1/auth/login` | None | 200, opaque refresh_token (not JWT) |
| S15 | Refresh → rotated tokens | `POST` | `/api/v1/auth/refresh` | None | 200, new token pair issued |
| S16 | Logout → revoke refresh | `POST` | `/api/v1/auth/logout` | None | 200, `LOGOUT_SUCCESS` |
| S17 | Revoked refresh → 401 | `POST` | `/api/v1/auth/refresh` | None | 401, `SESSION_INVALIDATED` |
| S18 | Fake refresh token → 401 | `POST` | `/api/v1/auth/refresh` | None | 401, `SESSION_INVALIDATED` |

**JWT_REFRESH_DAYS validated:**
- `create_refresh_token()` sets `expires_at = now + JWT_REFRESH_DAYS` (default: 30 days)
- S14 verifies refresh token is opaque (not JWT) — hash stored in DB, raw returned to client
- S15–S17 validate the full lifecycle: issue → rotate → revoke → reject

---

### 05 — Reset token validation

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S19 | Forgot password | `POST` | `/api/v1/auth/forgot-password` | None | 200, `FORGOT_PASSWORD_SENT` |
| S20 | Invalid reset token | `POST` | `/api/v1/auth/reset-password` | None | 400, `RESET_LINK_INVALID` |
| S21 | Non-existent email | `POST` | `/api/v1/auth/forgot-password` | None | 200, `FORGOT_PASSWORD_SENT` (no info leak) |

**How to get the reset token (S19):**

After running S19, check the backend logs:

```bash
docker compose -f docker-compose.local.yml --env-file .env.local logs backend --tail=5
```

Look for the line:
```
[RESET] Password reset link for superadmin@seed.lamviec360.com: http://localhost:3080/reset-password?token=eyJhbG...
```

Copy the `token=` value to use in S20's request body.

**What this validates:**
- `create_reset_token()` is called and a JWT is created (S19)
- `decode_reset_token()` rejects tampered tokens via `InvalidTokenException` (S20)
- No user enumeration — same response for existing and non-existing emails (S21)

---

### 06 — Centralised usage (no duplication)

| # | Request | Method | Endpoint | Auth | Expected |
|---|---------|--------|----------|------|----------|
| S22 | Login hr_recruiter | `POST` | `/api/v1/auth/login` | None | 200, same JWT structure as S02 |
| S23 | Response time < 500ms | `POST` | `/api/v1/auth/login` | None | 200, response time < 500ms |

**What this validates:**
- All roles use the same `create_access_token()` → consistent JWT structure (S22)
- No duplicate hashing or redundant computations → fast response (S23)

---

## Security Module Reference

| Function | File | Purpose |
|----------|------|---------|
| `create_access_token(user_id, role)` | `core/security.py` | Sign JWT with claims: `sub`, `role`, `type=access`, `iat`, `exp` |
| `create_refresh_token(user_id)` | `core/security.py` | Generate opaque token + SHA-256 hash + `expires_at` |
| `decode_access_token(token)` | `core/security.py` | Verify JWT → `TokenExpiredException` or `InvalidTokenException` |
| `hash_password(plain)` | `core/security.py` | argon2id hash with unique salt |
| `verify_password(plain, hashed)` | `core/security.py` | Returns `True` only for exact match |
| `create_reset_token(user_id)` | `core/security.py` | JWT with `type=password_reset`, 30min TTL |
| `decode_reset_token(token)` | `core/security.py` | Verify reset JWT with distinct exceptions |
| `create_invite_token(id, email)` | `core/security.py` | JWT with `type=team_invite`, 72h TTL |
| `decode_invite_token(token)` | `core/security.py` | Verify invite JWT with distinct exceptions |

---

## Environment Variables

| Variable | Default | Used by |
|----------|---------|---------|
| `JWT_SECRET` | `local-jwt-secret-change-in-production` | All JWT sign/verify |
| `JWT_ALGORITHM` | `HS256` | All JWT sign/verify |
| `JWT_EXPIRY_MINUTES` | `60` | `create_access_token` |
| `JWT_REFRESH_DAYS` | `30` | `create_refresh_token` |
| `INVITE_TTL_HOURS` | `72` | `create_invite_token` |

---

## Exception Handling

| Exception | HTTP Status | Response Code | When |
|-----------|-------------|---------------|------|
| `TokenExpiredException` | 401 | `TOKEN_EXPIRED` | JWT `exp` is in the past |
| `InvalidTokenException` | 401 | `SESSION_INVALIDATED` | Tampered, wrong secret, wrong type, malformed |

---

## Running the Collection

### In Postman UI

1. Import `US-002-Postman-Collection.json`
2. Ensure backend is running (`make up && make seed`)
3. Click **Run collection** → all 23 requests run sequentially

### Via Newman CLI

```bash
newman run docs/US-002-Postman-Collection.json --reporters cli
```

Expected: **23 requests, all passing** ✅

---

## Companion Unit Tests

The Postman collection is complemented by `tests/test_us002_security.py` (65 tests) which directly tests:
- JWT claims and expiry (AC1)
- Expired vs tampered exceptions (AC2)
- argon2 hash prefix and unique salt (AC3)
- Password verification edge cases (AC4)
- Config defaults and lifetime calculations (AC5)

Run:
```bash
make test
# or specifically:
docker compose -f docker-compose.local.yml --env-file .env.local exec backend pytest tests/test_us002_security.py -v
```
