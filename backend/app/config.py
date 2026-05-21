"""
Application configuration via pydantic-settings.
Reads from environment variables (injected via .env files in Docker).
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Environment ---
    ENVIRONMENT: str = "local"

    # --- PostgreSQL ---
    POSTGRES_DB: str = "lamviec360"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "localdev123"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Auth / JWT ---
    JWT_SECRET: str = "local-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    JWT_REFRESH_DAYS: int = 30

    # --- OTP ---
    OTP_TTL_MINUTES: int = 10

    # --- Team Invite ---
    INVITE_TTL_HOURS: int = 72

    # --- SendGrid ---
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "noreply@lamviec360.com"

    # --- Frontend ---
    FRONTEND_URL: str = "http://localhost:3080"

    # --- OAuth (placeholder — credentials pending) ---
    AUTH_GOOGLE_CLIENT_ID: str = ""
    AUTH_GOOGLE_CLIENT_SECRET: str = ""
    AUTH_ZALO_APP_ID: str = ""
    AUTH_ZALO_APP_SECRET: str = ""

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        return (
            f"postgresql://{quote_plus(self.POSTGRES_USER)}:"
            f"{quote_plus(self.POSTGRES_PASSWORD)}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
