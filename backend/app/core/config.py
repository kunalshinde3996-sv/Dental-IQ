"""Application settings, loaded from environment variables / backend/.env.

Secrets are never hard-coded: JWT_SECRET must come from the environment. In development a
missing secret is replaced by a random per-process value (tokens then reset on restart); in
production a missing or weak secret stops the app from starting.
"""
import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("dental_iq")

#: Values that must never be used as a real secret (copied from examples / docs).
_PLACEHOLDER_SECRETS = {"change-me-to-a-long-random-string", "dev-only-insecure-secret-change-me", "secret", "changeme"}
MIN_SECRET_LENGTH = 32


class ConfigError(RuntimeError):
    """Raised at start-up when production settings are unsafe."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Dental-IQ API"
    #: "development" or "production". Production enforces strong secrets and migrations-only schema.
    app_env: str = "development"
    # SQLite by default; set DATABASE_URL to a PostgreSQL URL to switch.
    database_url: str = "sqlite:///./dental_iq.db"
    # Dev convenience: create missing tables at start-up. Ignored (always off) in production,
    # where the schema is managed by `alembic upgrade head`.
    auto_create_tables: bool = True

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # one clinic shift

    # Brute-force protection for /api/auth/login (failed attempts per email+IP).
    login_max_failures: int = 5
    login_window_minutes: int = 15
    # Use X-Forwarded-For for the client IP (only behind a trusted reverse proxy).
    trust_proxy_headers: bool = False

    # The deployed Vercel frontend is included so the hosted demo works without extra config;
    # setting CORS_ORIGINS replaces this whole list.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://dental-iq-navy.vercel.app"
    # Where trained ML models and the seed's ground-truth file are written.
    ml_artifact_dir: str = str(Path(__file__).resolve().parents[2] / "ml" / "artifacts")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def create_tables_on_startup(self) -> bool:
        return self.auto_create_tables and not self.is_production

    def validate_security(self) -> None:
        """Fill or reject the JWT secret and CORS policy according to the environment."""
        weak = (not self.jwt_secret or self.jwt_secret in _PLACEHOLDER_SECRETS
                or len(self.jwt_secret) < MIN_SECRET_LENGTH)
        if self.is_production:
            if weak:
                raise ConfigError(f"APP_ENV=production requires JWT_SECRET of at least {MIN_SECRET_LENGTH} random "
                                  "characters (e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`).")
            if "*" in self.cors_origin_list:
                raise ConfigError("CORS_ORIGINS must list explicit origins in production, not '*'.")
        elif weak:
            logger.warning("JWT_SECRET is missing or weak: using a random per-process secret (development only). "
                           "Sessions reset when the server restarts.")
            self.jwt_secret = secrets.token_urlsafe(48)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_security()
    return settings


def artifact_dir() -> Path:
    path = Path(get_settings().ml_artifact_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
