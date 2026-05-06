"""
OAuth provider scaffolding — PRD Section 3.1 (AUTH-FR-002)

ACTIVATION INSTRUCTIONS:
  1. Set AUTH_GOOGLE_CLIENT_ID + AUTH_GOOGLE_CLIENT_SECRET in .env.local
  2. Set AUTH_ZALO_APP_ID + AUTH_ZALO_APP_SECRET in .env.local
  3. Restart the backend — the /api/v1/auth/google/* and /api/v1/auth/zalo/*
     endpoints become functional with zero code changes.

Each provider module must implement:
  - get_login_redirect_url() -> str
  - handle_callback(code: str) -> OAuthUserInfo
"""

from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass
class OAuthUserInfo:
    email: str
    full_name: str
    provider: str
    provider_user_id: str


# ── Google ─────────────────────────────────────────────────────────────

GOOGLE_ENABLED = bool(settings.AUTH_GOOGLE_CLIENT_ID and settings.AUTH_GOOGLE_CLIENT_SECRET)

# TODO: Replace stub URLs with real Google OAuth endpoints when credentials are available.
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def google_login_redirect_url(redirect_uri: str) -> str:
    """Return Google OAuth consent page URL.
    When AUTH_GOOGLE_CLIENT_ID is empty, returns a stub URL so the frontend
    can still render the button (disabled) and the endpoint doesn't 500.
    """
    if not GOOGLE_ENABLED:
        return f"{GOOGLE_AUTH_URL}?client_id=NOT_CONFIGURED&redirect_uri={redirect_uri}&response_type=code&scope=openid+email+profile"

    return (
        f"{GOOGLE_AUTH_URL}"
        f"?client_id={settings.AUTH_GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid+email+profile"
        f"&access_type=offline"
        f"&prompt=consent"
    )


async def google_handle_callback(code: str, redirect_uri: str) -> OAuthUserInfo:
    """Exchange authorization code for user info.
    Placeholder — returns a stub user until real credentials are configured.
    """
    if not GOOGLE_ENABLED:
        raise NotImplementedError("Google OAuth is not configured. Set AUTH_GOOGLE_CLIENT_ID and AUTH_GOOGLE_CLIENT_SECRET in .env.local")

    # TODO: implement real token exchange + userinfo fetch
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     token_resp = await client.post(GOOGLE_TOKEN_URL, data={...})
    #     userinfo_resp = await client.get(GOOGLE_USERINFO_URL, headers={...})
    raise NotImplementedError("Google OAuth callback not yet implemented.")


# ── Zalo ───────────────────────────────────────────────────────────────

ZALO_ENABLED = bool(settings.AUTH_ZALO_APP_ID and settings.AUTH_ZALO_APP_SECRET)

# TODO: Replace stub URLs with real Zalo OAuth endpoints when credentials are available.
ZALO_AUTH_URL = "https://oauth.zaloapp.com/v4/permission"
ZALO_TOKEN_URL = "https://oauth.zaloapp.com/v4/access_token"
ZALO_USERINFO_URL = "https://graph.zalo.me/v2.0/me"


def zalo_login_redirect_url(redirect_uri: str) -> str:
    """Return Zalo OAuth consent page URL."""
    if not ZALO_ENABLED:
        return f"{ZALO_AUTH_URL}?app_id=NOT_CONFIGURED&redirect_uri={redirect_uri}&state=zalo"

    return (
        f"{ZALO_AUTH_URL}"
        f"?app_id={settings.AUTH_ZALO_APP_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&state=zalo"
    )


async def zalo_handle_callback(code: str, redirect_uri: str) -> OAuthUserInfo:
    """Exchange authorization code for user info.
    Placeholder — returns a stub user until real credentials are configured.
    """
    if not ZALO_ENABLED:
        raise NotImplementedError("Zalo OAuth is not configured. Set AUTH_ZALO_APP_ID and AUTH_ZALO_APP_SECRET in .env.local")

    # TODO: implement real token exchange + userinfo fetch
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     token_resp = await client.post(ZALO_TOKEN_URL, data={...})
    #     userinfo_resp = await client.get(ZALO_USERINFO_URL, headers={...})
    raise NotImplementedError("Zalo OAuth callback not yet implemented.")
