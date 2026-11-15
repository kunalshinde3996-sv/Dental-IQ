"""Application settings, loaded from environment variables / backend/.env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Dental-IQ API"
    # SQLite by default; set DATABASE_URL to a PostgreSQL URL to switch.
    database_url: str = "sqlite:///./dental_iq.db"
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Where trained ML models and the seed's ground-truth file are written.
    ml_artifact_dir: str = str(Path(__file__).resolve().parents[2] / "ml" / "artifacts")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def artifact_dir() -> Path:
    path = Path(get_settings().ml_artifact_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
