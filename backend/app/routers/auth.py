"""
Auth API router — all endpoints under /api/v1/auth
PRD Section 3.1 — AUTH-FR-001 to AUTH-FR-009
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_lang, require_role
from app.core.i18n import Lang
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    InviteAcceptRequest,
    InviteAcceptResponse,
    InviteCreateRequest,
    InviteCreateResponse,
    InviteDetailResponse,
    Login2FARequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MessageResponse,
    OTPResendRequest,
    OTPResendResponse,
    RefreshRequest,
    RegisterStep2Request,
    RegisterStep2Response,
    RegisterVerifyRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    UserOut,
    FirstLoginCompleteResponse,
    AbuseEventResponse,
)
from app.services import auth_service
from app.services.oauth_providers import (
    google_login_redirect_url,
    zalo_login_redirect_url,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Registration (AUTH-FR-001) ────────────────────────────────────────

@router.post("/register/step2", response_model=RegisterStep2Response, status_code=status.HTTP_201_CREATED)
def register_step2(body: RegisterStep2Request, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.register_step2(
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        password=body.password,
        account_type=body.account_type,
        consent_given=body.consent_given,
        db=db,
        lang=lang,
    )


@router.post("/register/verify", response_model=TokenResponse)
def register_verify(body: RegisterVerifyRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.register_verify(body.user_id, body.otp_code, db, lang)


# ── Login (AUTH-FR-002, AUTH-FR-009) ──────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.login(body.email, body.password, db, lang)


@router.post("/login/2fa", response_model=TokenResponse)
def login_2fa(body: Login2FARequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.login_2fa(body.user_id, body.otp_code, db, lang)


# ── OTP Resend (AUTH-FR-003) ─────────────────────────────────────────

@router.post("/otp/resend", response_model=OTPResendResponse)
def otp_resend(body: OTPResendRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.resend_otp(body.user_id, body.purpose, db, lang)


# ── Token Refresh (AUTH-FR-006) ──────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.refresh_tokens(body.refresh_token, db, lang)


# ── Logout ────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
def logout(body: LogoutRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.logout(body.refresh_token, db, lang)


# ── Forgot / Reset Password (AUTH-FR-004) ────────────────────────────

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.forgot_password(body.email, db, lang)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.reset_password(body.token, body.new_password, db, lang)


# ── Team Invite (AUTH-FR-007) ────────────────────────────────────────

@router.post(
    "/invite",
    response_model=InviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_invite(
    body: InviteCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.company_admin, UserRole.super_admin)),
    lang: Lang = Depends(get_lang),
):
    return auth_service.create_invitation(
        email=body.email,
        role=body.role,
        company_id=body.company_id,
        invited_by=current_user.id,
        db=db,
        lang=lang,
    )


@router.get("/invite/{token}", response_model=InviteDetailResponse)
def get_invite(token: str, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.get_invitation(token, db, lang)


@router.post("/invite/accept", response_model=InviteAcceptResponse)
def accept_invite(body: InviteAcceptRequest, db: Session = Depends(get_db), lang: Lang = Depends(get_lang)):
    return auth_service.accept_invitation(body.token, body.full_name, body.password, db, lang)


# ── OAuth Redirects (placeholder) ────────────────────────────────────

@router.get("/google/login")
def google_login(request: Request):
    redirect_uri = str(request.url_for("google_callback"))
    url = google_login_redirect_url(redirect_uri)
    return RedirectResponse(url=url)


@router.get("/google/callback", name="google_callback")
async def google_callback(code: str = "", db: Session = Depends(get_db)):
    """Placeholder — will exchange code for tokens when Google credentials are set."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google OAuth not configured. Please set AUTH_GOOGLE_CLIENT_ID in .env.local.",
    )


@router.get("/zalo/login")
def zalo_login(request: Request):
    redirect_uri = str(request.url_for("zalo_callback"))
    url = zalo_login_redirect_url(redirect_uri)
    return RedirectResponse(url=url)


@router.get("/zalo/callback", name="zalo_callback")
async def zalo_callback(code: str = "", db: Session = Depends(get_db)):
    """Placeholder — will exchange code for tokens when Zalo credentials are set."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Zalo OAuth not configured. Please set AUTH_ZALO_APP_ID in .env.local.",
    )


# ── Me / Profile ─────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── First Login Complete (AUTH-FR-008) ────────────────────────────────

@router.post("/first-login-complete", response_model=FirstLoginCompleteResponse)
def first_login_complete(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Lang = Depends(get_lang),
):
    return auth_service.complete_first_login(current_user, db, lang)


# ── AI Abuse (BR-006) ────────────────────────────────────────────────

@router.post("/ai-abuse", response_model=AbuseEventResponse)
def ai_abuse(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    lang: Lang = Depends(get_lang),
):
    return auth_service.record_ai_abuse(current_user, db, lang)
