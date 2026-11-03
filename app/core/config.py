"""
RouteWise application configuration.

Uses pydantic-settings to load configuration from environment variables
and .env files with proper validation and type coercion.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "RouteWise"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── API ───────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./routewise.db"
    POSTGIS_AVAILABLE: bool = False

    # ── Redis ─────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / JWT ────────────────────────────────────────────────────────
    SECRET_KEY: str  # required – no default
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    # ── Celery ────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # ── Routing engine (OSRM / Valhalla / etc.) ──────────────────────────
    ROUTING_ENGINE_URL: str = ""

    # ── Provider API keys (all optional) ──────────────────────────────────
    UBER_API_KEY: str = ""
    OLA_API_KEY: str = ""
    RAPIDO_API_KEY: str = ""
    NAMMA_YATRI_API_KEY: str = ""

    # ── Demo / feature flags ──────────────────────────────────────────────
    DEMO_MODE: bool = True

    # ── Search & distance constraints ─────────────────────────────────────
    MAX_WALKING_DISTANCE_M: int = 2000
    MAX_SEARCH_RADIUS_M: int = 5000
    DEFAULT_SEARCH_RADIUS_M: int = 1500

    # ── Rate limiting ─────────────────────────────────────────────────────
    RATE_LIMIT: str = "60/minute"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton per process)."""
    return Settings()  # type: ignore[call-arg]
