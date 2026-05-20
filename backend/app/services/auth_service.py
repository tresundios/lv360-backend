"""
Auth business logic — PRD Section 3.1
Covers: registration, login, OTP, password reset, invite, token refresh, AI abuse.
"""

import random
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.i18n import DEFAULT_LANG, Lang, MessageCode, t
from app.core.security import (
    create_access_token,
    create_invite_token,
    create_refresh_token,
    create_reset_token,
    decode_invite_token,
    decode_reset_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import (
    AccountType,
    RefreshToken,
    SocialAccount,
    TeamInvitation,
    User,
    UserRole,
    UserStatus,
)
from app.redis_client import get_redis_client

settings = get_settings()


# ── Helpers ────────────────────────────────────────────────────────────

def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _otp_redis_key(user_id: UUID, purpose: str) -> str:
    return f"otp:{user_id}:{purpose}"


def _otp_resend_key(user_id: UUID, purpose: str) -> str:
    return f"otp_resend:{user_id}:{purpose}"


def _role_for_account_type(account_type: AccountType) -> UserRole:
    if account_type == AccountType.employer:
        return UserRole.company_admin
    return UserRole.job_seeker


def _issue_tokens(user: User, db: Session) -> dict:
    """Create access + refresh token pair, persist refresh hash."""
    access = create_access_token(user.id, user.role.value)
    raw_refresh, token_hash, expires_at = create_refresh_token(user.id)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(rt)

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return {
        "access_token": access,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "user": user,
    }


# ── Registration ───────────────────────────────────────────────────────

def register_step2(
    full_name: str,
    email: str,
    phone: str,
    password: str,
    account_type: AccountType,
    consent_given: bool,
    db: Session,
    lang: Lang = DEFAULT_LANG,
) -> dict:
    """Create user (pending) + store OTP in Redis. Returns user_id."""
    # BR-011: consent mandatory for job seekers
    if account_type == AccountType.job_seeker and not consent_given:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": MessageCode.CONSENT_REQUIRED, "message": t(MessageCode.CONSENT_REQUIRED, lang)},
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": MessageCode.EMAIL_TAKEN, "message": t(MessageCode.EMAIL_TAKEN, lang)},
        )

    role = _role_for_account_type(account_type)

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=role,
        account_type=account_type,
        status=UserStatus.pending,
        consent_given=consent_given,
        consent_timestamp=datetime.now(timezone.utc) if consent_given else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Store OTP in Redis
    otp = _generate_otp()
    redis = get_redis_client()
    ttl = settings.OTP_TTL_MINUTES * 60
    redis.setex(_otp_redis_key(user.id, "registration"), ttl, otp)
    redis.setex(_otp_resend_key(user.id, "registration"), ttl, "3")  # max 3 resends

    # TODO: send OTP via SMS/email (SendGrid) in production
    print(f"[OTP] Registration OTP for {user.email}: {otp}")

    return {"user_id": user.id, "code": MessageCode.OTP_SENT, "message": t(MessageCode.OTP_SENT, lang)}


def register_verify(user_id: UUID, otp_code: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Verify registration OTP → activate user → return tokens."""
    redis = get_redis_client()
    key = _otp_redis_key(user_id, "registration")
    stored = redis.get(key)

    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": MessageCode.OTP_EXPIRED, "message": t(MessageCode.OTP_EXPIRED, lang)},
        )

    if stored != otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": MessageCode.OTP_INVALID, "message": t(MessageCode.OTP_INVALID, lang)},
        )

    redis.delete(key)
    redis.delete(_otp_resend_key(user_id, "registration"))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": MessageCode.USER_NOT_FOUND, "message": t(MessageCode.USER_NOT_FOUND, lang)},
        )

    user.status = UserStatus.active
    db.commit()

    return _issue_tokens(user, db)


# ── Login ──────────────────────────────────────────────────────────────

def login(email: str, password: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Authenticate user. company_admin requires 2FA."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.INVALID_CREDENTIALS, "message": t(MessageCode.INVALID_CREDENTIALS, lang)},
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.INVALID_CREDENTIALS, "message": t(MessageCode.INVALID_CREDENTIALS, lang)},
        )

    if user.status == UserStatus.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": MessageCode.ACCOUNT_SUSPENDED, "message": t(MessageCode.ACCOUNT_SUSPENDED, lang)},
        )

    if user.status == UserStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": MessageCode.ACCOUNT_PENDING, "message": t(MessageCode.ACCOUNT_PENDING, lang)},
        )

    # company_admin requires 2FA (AUTH-FR-009)
    if user.role == UserRole.company_admin:
        otp = _generate_otp()
        redis = get_redis_client()
        ttl = settings.OTP_TTL_MINUTES * 60
        redis.setex(_otp_redis_key(user.id, "login_2fa"), ttl, otp)
        redis.setex(_otp_resend_key(user.id, "login_2fa"), ttl, "3")
        print(f"[OTP] 2FA OTP for {user.email}: {otp}")

        return {
            "access_token": "",
            "refresh_token": "",
            "token_type": "bearer",
            "user": user,
            "requires_2fa": True,
        }

    return {**_issue_tokens(user, db), "requires_2fa": False}


def login_2fa(user_id: UUID, otp_code: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Verify 2FA OTP for company_admin login."""
    redis = get_redis_client()
    key = _otp_redis_key(user_id, "login_2fa")
    stored = redis.get(key)

    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": MessageCode.OTP_EXPIRED, "message": t(MessageCode.OTP_EXPIRED, lang)},
        )

    if stored != otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": MessageCode.OTP_INVALID, "message": t(MessageCode.OTP_INVALID, lang)},
        )

    redis.delete(key)
    redis.delete(_otp_resend_key(user_id, "login_2fa"))

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": MessageCode.USER_NOT_FOUND, "message": t(MessageCode.USER_NOT_FOUND, lang)},
        )

    return {**_issue_tokens(user, db), "requires_2fa": False}


# ── OTP Resend ─────────────────────────────────────────────────────────

def resend_otp(user_id: UUID, purpose: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Resend OTP — max 3 attempts per session."""
    redis = get_redis_client()
    resend_key = _otp_resend_key(user_id, purpose)
    remaining_raw = redis.get(resend_key)

    if remaining_raw is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": MessageCode.OTP_START_OVER, "message": t(MessageCode.OTP_START_OVER, lang)},
        )

    remaining = int(remaining_raw)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": MessageCode.OTP_RESEND_LIMIT, "message": t(MessageCode.OTP_RESEND_LIMIT, lang)},
        )

    otp = _generate_otp()
    ttl = settings.OTP_TTL_MINUTES * 60
    redis.setex(_otp_redis_key(user_id, purpose), ttl, otp)
    redis.setex(resend_key, ttl, str(remaining - 1))

    user = db.query(User).filter(User.id == user_id).first()
    print(f"[OTP] Resend OTP for {user.email if user else user_id}: {otp}")

    return {"code": MessageCode.OTP_RESENT, "message": t(MessageCode.OTP_RESENT, lang), "remaining_attempts": remaining - 1}


# ── Token Refresh ──────────────────────────────────────────────────────

def refresh_tokens(raw_refresh: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Exchange valid refresh token for new access + refresh pair."""
    token_hash = hash_token(raw_refresh)
    rt = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )

    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.SESSION_INVALIDATED, "message": t(MessageCode.SESSION_INVALIDATED, lang)},
        )

    # Revoke old
    rt.revoked = True
    db.commit()

    user = db.query(User).filter(User.id == rt.user_id).first()
    if not user or user.status == UserStatus.suspended:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.ACCOUNT_INVALID, "message": t(MessageCode.ACCOUNT_INVALID, lang)},
        )

    return _issue_tokens(user, db)


# ── Logout ─────────────────────────────────────────────────────────────

def logout(raw_refresh: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Revoke refresh token."""
    token_hash = hash_token(raw_refresh)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if rt:
        rt.revoked = True
        db.commit()
    return {"code": MessageCode.LOGOUT_SUCCESS, "message": t(MessageCode.LOGOUT_SUCCESS, lang)}


# ── Forgot / Reset Password ───────────────────────────────────────────

def forgot_password(email: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Send password-reset link (JWT, 30 min). Always return success to avoid email enumeration."""
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = create_reset_token(user.id)
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        # TODO: send via SendGrid in production
        print(f"[RESET] Password reset link for {user.email}: {reset_link}")

    return {"code": MessageCode.FORGOT_PASSWORD_SENT, "message": t(MessageCode.FORGOT_PASSWORD_SENT, lang)}


def reset_password(token: str, new_password: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Validate reset JWT → update password → revoke all refresh tokens."""
    payload = decode_reset_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": MessageCode.RESET_LINK_INVALID, "message": t(MessageCode.RESET_LINK_INVALID, lang)},
        )

    user_id = UUID(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": MessageCode.USER_NOT_FOUND, "message": t(MessageCode.USER_NOT_FOUND, lang)},
        )

    user.password_hash = hash_password(new_password)

    # Revoke ALL refresh tokens (AUTH-FR-004 / BR)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,  # noqa: E712
    ).update({"revoked": True})

    db.commit()
    return {"code": MessageCode.PASSWORD_RESET_SUCCESS, "message": t(MessageCode.PASSWORD_RESET_SUCCESS, lang)}


# ── Team Invite ────────────────────────────────────────────────────────

def create_invitation(email: str, role: UserRole, company_id: UUID, invited_by: UUID, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Create team invite → send email with JWT link."""
    from uuid import uuid4

    invite_id = uuid4()
    jwt_token, token_hash = create_invite_token(invite_id, email)

    invitation = TeamInvitation(
        id=invite_id,
        company_id=company_id,
        invited_by=invited_by,
        email=email,
        role=role,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.INVITE_TTL_HOURS),
    )
    db.add(invitation)
    db.commit()

    invite_link = f"{settings.FRONTEND_URL}/invite/{jwt_token}"
    # TODO: send via SendGrid in production
    print(f"[INVITE] Team invite for {email}: {invite_link}")

    return {"invitation_id": invite_id, "code": MessageCode.INVITE_SENT, "message": t(MessageCode.INVITE_SENT, lang)}


def get_invitation(token: str, db: Session, lang: Lang = DEFAULT_LANG) -> TeamInvitation:
    """Validate invite JWT → return invitation details."""
    payload = decode_invite_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": MessageCode.INVITE_INVALID, "message": t(MessageCode.INVITE_INVALID, lang)},
        )

    invite_id = UUID(payload["sub"])
    invitation = db.query(TeamInvitation).filter(TeamInvitation.id == invite_id).first()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": MessageCode.INVITE_NOT_FOUND, "message": t(MessageCode.INVITE_NOT_FOUND, lang)},
        )

    if invitation.revoked or invitation.accepted:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": MessageCode.INVITE_USED_OR_REVOKED, "message": t(MessageCode.INVITE_USED_OR_REVOKED, lang)},
        )

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": MessageCode.INVITE_EXPIRED, "message": t(MessageCode.INVITE_EXPIRED, lang)},
        )

    return invitation


def accept_invitation(token: str, full_name: str, password: str, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    """Accept invite → create user → return tokens."""
    invitation = get_invitation(token, db, lang)

    existing = db.query(User).filter(User.email == invitation.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": MessageCode.EMAIL_TAKEN, "message": t(MessageCode.EMAIL_TAKEN, lang)},
        )

    account_type = AccountType.employer if invitation.role in (
        UserRole.company_admin, UserRole.hr_recruiter, UserRole.viewer
    ) else AccountType.job_seeker

    user = User(
        email=invitation.email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=invitation.role,
        account_type=account_type,
        status=UserStatus.active,
    )
    db.add(user)

    invitation.accepted = True
    db.commit()
    db.refresh(user)

    return _issue_tokens(user, db)


# ── First Login Complete ───────────────────────────────────────────────

def complete_first_login(user: User, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    user.first_login_complete = True
    db.commit()
    return {"code": MessageCode.ONBOARDING_COMPLETE, "message": t(MessageCode.ONBOARDING_COMPLETE, lang), "first_login_complete": True}


# ── AI Abuse (BR-006) ─────────────────────────────────────────────────

def record_ai_abuse(user: User, db: Session, lang: Lang = DEFAULT_LANG) -> dict:
    user.ai_abuse_count += 1
    terminated = False

    if user.ai_abuse_count > 3:
        # Revoke all refresh tokens
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked == False,  # noqa: E712
        ).update({"revoked": True})
        terminated = True

    db.commit()
    db.refresh(user)

    if terminated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.SESSION_TERMINATED, "message": t(MessageCode.SESSION_TERMINATED, lang)},
        )

    return {"ai_abuse_count": user.ai_abuse_count, "session_terminated": False}


# ── Me ─────────────────────────────────────────────────────────────────

def get_me(user: User) -> User:
    return user
