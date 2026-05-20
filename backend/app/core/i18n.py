"""
Internationalization (i18n) support — English + Vietnamese.
Returns both a machine-readable code and a localized message.

Usage:
    from app.core.i18n import t, MessageCode
    t(MessageCode.EMAIL_TAKEN, lang="vi")  → "Email đã được sử dụng."
    t(MessageCode.EMAIL_TAKEN, lang="en")  → "Email is already in use."
"""

from enum import Enum
from typing import Literal

Lang = Literal["vi", "en"]
DEFAULT_LANG: Lang = "vi"


class MessageCode(str, Enum):
    """Machine-readable message codes returned alongside localized text."""

    # ── Registration ──────────────────────────────────────────────────
    ACCOUNT_TYPE_SELECTED = "ACCOUNT_TYPE_SELECTED"
    OTP_SENT = "OTP_SENT"
    OTP_RESENT = "OTP_RESENT"
    OTP_EXPIRED = "OTP_EXPIRED"
    OTP_INVALID = "OTP_INVALID"
    OTP_START_OVER = "OTP_START_OVER"
    OTP_RESEND_LIMIT = "OTP_RESEND_LIMIT"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # ── Login ─────────────────────────────────────────────────────────
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"
    ACCOUNT_PENDING = "ACCOUNT_PENDING"

    # ── Logout ────────────────────────────────────────────────────────
    LOGOUT_SUCCESS = "LOGOUT_SUCCESS"

    # ── Token / Session ───────────────────────────────────────────────
    SESSION_INVALIDATED = "SESSION_INVALIDATED"
    ACCOUNT_INVALID = "ACCOUNT_INVALID"

    # ── Password Reset ────────────────────────────────────────────────
    FORGOT_PASSWORD_SENT = "FORGOT_PASSWORD_SENT"
    PASSWORD_RESET_SUCCESS = "PASSWORD_RESET_SUCCESS"
    RESET_LINK_INVALID = "RESET_LINK_INVALID"

    # ── Invite ────────────────────────────────────────────────────────
    INVITE_SENT = "INVITE_SENT"
    INVITE_INVALID = "INVITE_INVALID"
    INVITE_NOT_FOUND = "INVITE_NOT_FOUND"
    INVITE_USED_OR_REVOKED = "INVITE_USED_OR_REVOKED"
    INVITE_EXPIRED = "INVITE_EXPIRED"

    # ── First login ───────────────────────────────────────────────────
    ONBOARDING_COMPLETE = "ONBOARDING_COMPLETE"

    # ── AI Abuse ──────────────────────────────────────────────────────
    SESSION_TERMINATED = "SESSION_TERMINATED"


# ── Translation dictionaries ──────────────────────────────────────────

_TRANSLATIONS: dict[MessageCode, dict[Lang, str]] = {
    # Registration
    MessageCode.ACCOUNT_TYPE_SELECTED: {
        "vi": "Đã chọn loại tài khoản.",
        "en": "Account type selected.",
    },
    MessageCode.OTP_SENT: {
        "vi": "OTP đã được gửi. Vui lòng kiểm tra.",
        "en": "OTP has been sent. Please check your inbox.",
    },
    MessageCode.OTP_RESENT: {
        "vi": "OTP đã được gửi lại.",
        "en": "OTP has been resent.",
    },
    MessageCode.OTP_EXPIRED: {
        "vi": "OTP đã hết hạn. Vui lòng yêu cầu mã mới.",
        "en": "OTP has expired. Please request a new code.",
    },
    MessageCode.OTP_INVALID: {
        "vi": "OTP không chính xác.",
        "en": "Invalid OTP code.",
    },
    MessageCode.OTP_START_OVER: {
        "vi": "OTP đã hết hạn. Vui lòng bắt đầu lại.",
        "en": "OTP has expired. Please start over.",
    },
    MessageCode.OTP_RESEND_LIMIT: {
        "vi": "Bạn đã vượt quá số lần gửi lại OTP (tối đa 3).",
        "en": "You have exceeded the OTP resend limit (max 3).",
    },
    MessageCode.CONSENT_REQUIRED: {
        "vi": "Người tìm việc phải đồng ý với điều khoản sử dụng (BR-011).",
        "en": "Job seekers must agree to the terms of use (BR-011).",
    },
    MessageCode.EMAIL_TAKEN: {
        "vi": "Email đã được sử dụng.",
        "en": "Email is already in use.",
    },
    MessageCode.USER_NOT_FOUND: {
        "vi": "Người dùng không tồn tại.",
        "en": "User not found.",
    },
    # Login
    MessageCode.INVALID_CREDENTIALS: {
        "vi": "Email hoặc mật khẩu không chính xác.",
        "en": "Invalid email or password.",
    },
    MessageCode.ACCOUNT_SUSPENDED: {
        "vi": "Tài khoản đã bị tạm ngưng.",
        "en": "Account has been suspended.",
    },
    MessageCode.ACCOUNT_PENDING: {
        "vi": "Tài khoản chưa được xác minh. Vui lòng xác minh OTP.",
        "en": "Account not yet verified. Please verify your OTP.",
    },
    # Logout
    MessageCode.LOGOUT_SUCCESS: {
        "vi": "Đăng xuất thành công.",
        "en": "Logged out successfully.",
    },
    # Token / Session
    MessageCode.SESSION_INVALIDATED: {
        "vi": "Phiên đã hết hạn. Vui lòng đăng nhập lại.",
        "en": "Session expired. Please log in again.",
    },
    MessageCode.ACCOUNT_INVALID: {
        "vi": "Tài khoản không hợp lệ.",
        "en": "Invalid account.",
    },
    # Password Reset
    MessageCode.FORGOT_PASSWORD_SENT: {
        "vi": "Nếu email tồn tại, chúng tôi đã gửi liên kết đặt lại mật khẩu.",
        "en": "If the email exists, we have sent a password reset link.",
    },
    MessageCode.PASSWORD_RESET_SUCCESS: {
        "vi": "Mật khẩu đã được đặt lại thành công.",
        "en": "Password has been reset successfully.",
    },
    MessageCode.RESET_LINK_INVALID: {
        "vi": "Liên kết đặt lại không hợp lệ hoặc đã hết hạn.",
        "en": "Reset link is invalid or has expired.",
    },
    # Invite
    MessageCode.INVITE_SENT: {
        "vi": "Lời mời đã được gửi.",
        "en": "Invitation has been sent.",
    },
    MessageCode.INVITE_INVALID: {
        "vi": "Lời mời không hợp lệ hoặc đã hết hạn.",
        "en": "Invitation is invalid or has expired.",
    },
    MessageCode.INVITE_NOT_FOUND: {
        "vi": "Lời mời không tồn tại.",
        "en": "Invitation not found.",
    },
    MessageCode.INVITE_USED_OR_REVOKED: {
        "vi": "Lời mời đã được sử dụng hoặc thu hồi.",
        "en": "Invitation has been used or revoked.",
    },
    MessageCode.INVITE_EXPIRED: {
        "vi": "Lời mời đã hết hạn.",
        "en": "Invitation has expired.",
    },
    # First login
    MessageCode.ONBOARDING_COMPLETE: {
        "vi": "Onboarding đã hoàn tất.",
        "en": "Onboarding complete.",
    },
    # AI Abuse
    MessageCode.SESSION_TERMINATED: {
        "vi": "Phiên đã bị chấm dứt do vi phạm.",
        "en": "Session terminated due to policy violation.",
    },
}


def t(code: MessageCode, lang: Lang = DEFAULT_LANG) -> str:
    """Translate a message code to a localized string."""
    translations = _TRANSLATIONS.get(code)
    if not translations:
        return code.value
    return translations.get(lang, translations.get("vi", code.value))


def parse_accept_language(header: str | None) -> Lang:
    """Parse Accept-Language header → return 'en' or 'vi' (default)."""
    if not header:
        return DEFAULT_LANG
    header_lower = header.lower().strip()
    if header_lower.startswith("en"):
        return "en"
    return "vi"
