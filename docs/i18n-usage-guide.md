# i18n Usage Guide — English + Vietnamese

## Overview

The backend supports bilingual responses (English & Vietnamese) via the `Accept-Language` HTTP header. Every API response includes both a machine-readable `code` and a human-readable localized `message`.

---

## Quick Start

| Header | Language |
|--------|----------|
| `Accept-Language: en` | English |
| `Accept-Language: vi` | Vietnamese |
| *(no header)* | Vietnamese (default) |

---

## Response Format

### Success responses

```json
{
  "code": "LOGOUT_SUCCESS",
  "message": "Logged out successfully."
}
```

### Error responses

```json
{
  "detail": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password."
  }
}
```

---

## Message Codes Reference

| Code | English | Vietnamese |
|------|---------|------------|
| `ACCOUNT_TYPE_SELECTED` | Account type selected. | Đã chọn loại tài khoản. |
| `OTP_SENT` | OTP has been sent. Please check your inbox. | OTP đã được gửi. Vui lòng kiểm tra. |
| `OTP_RESENT` | OTP has been resent. | OTP đã được gửi lại. |
| `OTP_EXPIRED` | OTP has expired. Please request a new code. | OTP đã hết hạn. Vui lòng yêu cầu mã mới. |
| `OTP_INVALID` | Invalid OTP code. | OTP không chính xác. |
| `OTP_START_OVER` | OTP has expired. Please start over. | OTP đã hết hạn. Vui lòng bắt đầu lại. |
| `OTP_RESEND_LIMIT` | You have exceeded the OTP resend limit (max 3). | Bạn đã vượt quá số lần gửi lại OTP (tối đa 3). |
| `CONSENT_REQUIRED` | Job seekers must agree to the terms of use (BR-011). | Người tìm việc phải đồng ý với điều khoản sử dụng (BR-011). |
| `EMAIL_TAKEN` | Email is already in use. | Email đã được sử dụng. |
| `USER_NOT_FOUND` | User not found. | Người dùng không tồn tại. |
| `INVALID_CREDENTIALS` | Invalid email or password. | Email hoặc mật khẩu không chính xác. |
| `ACCOUNT_SUSPENDED` | Account has been suspended. | Tài khoản đã bị tạm ngưng. |
| `ACCOUNT_PENDING` | Account not yet verified. Please verify your OTP. | Tài khoản chưa được xác minh. Vui lòng xác minh OTP. |
| `LOGOUT_SUCCESS` | Logged out successfully. | Đăng xuất thành công. |
| `SESSION_INVALIDATED` | Session expired. Please log in again. | Phiên đã hết hạn. Vui lòng đăng nhập lại. |
| `ACCOUNT_INVALID` | Invalid account. | Tài khoản không hợp lệ. |
| `FORGOT_PASSWORD_SENT` | If the email exists, we have sent a password reset link. | Nếu email tồn tại, chúng tôi đã gửi liên kết đặt lại mật khẩu. |
| `PASSWORD_RESET_SUCCESS` | Password has been reset successfully. | Mật khẩu đã được đặt lại thành công. |
| `RESET_LINK_INVALID` | Reset link is invalid or has expired. | Liên kết đặt lại không hợp lệ hoặc đã hết hạn. |
| `INVITE_SENT` | Invitation has been sent. | Lời mời đã được gửi. |
| `INVITE_INVALID` | Invitation is invalid or has expired. | Lời mời không hợp lệ hoặc đã hết hạn. |
| `INVITE_NOT_FOUND` | Invitation not found. | Lời mời không tồn tại. |
| `INVITE_USED_OR_REVOKED` | Invitation has been used or revoked. | Lời mời đã được sử dụng hoặc thu hồi. |
| `INVITE_EXPIRED` | Invitation has expired. | Lời mời đã hết hạn. |
| `ONBOARDING_COMPLETE` | Onboarding complete. | Onboarding đã hoàn tất. |
| `SESSION_TERMINATED` | Session terminated due to policy violation. | Phiên đã bị chấm dứt do vi phạm. |

---

## Backend Architecture

```
app/core/i18n.py          ← MessageCode enum + translations dict + t() helper
app/core/deps.py          ← get_lang() dependency (parses Accept-Language header)
app/routers/auth.py       ← injects lang: Lang = Depends(get_lang) into endpoints
app/services/auth_service.py ← all functions accept lang parameter
app/schemas/auth.py       ← response schemas have code + message fields
```

### Adding a new message

1. Add enum value to `MessageCode` in `app/core/i18n.py`
2. Add translations to `_TRANSLATIONS` dict:

```python
MessageCode.MY_NEW_CODE: {
    "vi": "Nội dung tiếng Việt.",
    "en": "English content.",
},
```

3. Use in service: `t(MessageCode.MY_NEW_CODE, lang)`

### Adding a new language

1. Update `Lang` type in `app/core/i18n.py`:
```python
Lang = Literal["vi", "en", "ja"]  # add new language code
```

2. Add translations for every `MessageCode` in `_TRANSLATIONS`
3. Update `parse_accept_language()` to detect the new language

---

## Frontend Integration

### Axios (React/Vue)

```typescript
import axios from 'axios';

// Set globally based on user preference
const userLocale = localStorage.getItem('locale') || 'vi';
axios.defaults.headers.common['Accept-Language'] = userLocale;
```

### Per-request override

```typescript
const response = await axios.post('/api/v1/auth/login', body, {
  headers: { 'Accept-Language': 'en' }
});
```

### Handling responses

```typescript
// Success responses
interface ApiMessage {
  code: string;
  message: string;
}

// Error responses
interface ApiError {
  detail: {
    code: string;
    message: string;
  };
}

// Use code for programmatic logic, message for display
if (error.response?.data?.detail?.code === 'SESSION_TERMINATED') {
  // Force logout
  authStore.clear();
  router.push('/login');
}
```

---

## Postman Testing

Add `Accept-Language` header to requests:

| Header Key | Value | Result |
|-----------|-------|--------|
| `Accept-Language` | `en` | English messages |
| `Accept-Language` | `vi` | Vietnamese messages |
| *(omit header)* | — | Vietnamese (default) |

### Example in Postman

1. Go to request **Headers** tab
2. Add: `Accept-Language` = `en`
3. Send request
4. Response will contain English messages

---

## cURL Examples

```bash
# English
curl -s http://localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -H "Accept-Language: en" \
  -d '{"refresh_token": "..."}' | jq

# Vietnamese (default)
curl -s http://localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}' | jq
```

---

## Design Decisions

- **Default language:** Vietnamese (`vi`) — no header required for Vietnamese users
- **Stateless:** Language is determined per-request, not stored server-side
- **Backward-compatible:** Existing clients without `Accept-Language` header continue to receive Vietnamese
- **Machine-readable codes:** Frontend can use `code` for logic regardless of display language
- **No info leakage:** Endpoints like forgot-password always return same code/message regardless of email existence
