"""
Pydantic v2 request/response schemas for all auth endpoints.
PRD Section 3.1 — AUTH-FR-001 to AUTH-FR-009
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Enums (mirror SQLAlchemy enums for Pydantic) ──────────────────────

from app.models.user import AccountType, UserRole, UserStatus  # re-export


# ── User response ─────────────────────────────────────────────────────

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    phone: str | None = None
    role: UserRole
    account_type: AccountType | None = None
    status: UserStatus
    first_login_complete: bool
    created_at: datetime


# ── Registration (AUTH-FR-001) ────────────────────────────────────────

class RegisterStep1Request(BaseModel):
    """Step 1: account type selection."""
    account_type: AccountType


class RegisterStep1Response(BaseModel):
    account_type: AccountType
    code: str
    message: str


class RegisterStep2Request(BaseModel):
    """Step 2: profile details + send OTP."""
    account_type: AccountType
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+84\d{9,10}$")
    password: str = Field(..., min_length=8, max_length=128)
    consent_given: bool = False


class RegisterStep2Response(BaseModel):
    user_id: UUID
    code: str
    message: str


class RegisterVerifyRequest(BaseModel):
    """Step 3: verify OTP → return JWT."""
    user_id: UUID
    otp_code: str = Field(..., min_length=6, max_length=6)


# ── Login (AUTH-FR-002, AUTH-FR-009) ──────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
    requires_2fa: bool = False


class Login2FARequest(BaseModel):
    """Company Admin OTP step (AUTH-FR-009)."""
    user_id: UUID
    otp_code: str = Field(..., min_length=6, max_length=6)


# ── Token refresh (AUTH-FR-006) ───────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Logout ────────────────────────────────────────────────────────────

class LogoutRequest(BaseModel):
    refresh_token: str


# ── Forgot / Reset password (AUTH-FR-004) ─────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    code: str
    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ResetPasswordResponse(BaseModel):
    code: str
    message: str


# ── OTP resend (AUTH-FR-003) ──────────────────────────────────────────

class OTPResendRequest(BaseModel):
    user_id: UUID
    purpose: str = "registration"  # "registration" | "login_2fa"


class OTPResendResponse(BaseModel):
    code: str
    message: str
    remaining_attempts: int


# ── Team invite (AUTH-FR-007) ─────────────────────────────────────────

class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: UserRole
    company_id: UUID


class InviteCreateResponse(BaseModel):
    invitation_id: UUID
    invite_token: str
    code: str
    message: str


class InviteDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: UserRole
    company_id: UUID
    expires_at: datetime
    accepted: bool


class InviteAcceptRequest(BaseModel):
    token: str
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class InviteAcceptResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


# ── First login (AUTH-FR-008) ─────────────────────────────────────────

class FirstLoginCompleteResponse(BaseModel):
    code: str
    message: str
    first_login_complete: bool = True


# ── AI abuse (AUTH-FR-006 / BR) ───────────────────────────────────────

class AbuseEventResponse(BaseModel):
    ai_abuse_count: int
    session_terminated: bool = False


# ── Generic ───────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    code: str
    message: str
