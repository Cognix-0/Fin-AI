from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS = {
    "change-this-secret",
    "change-this-to-a-long-random-secret-at-least-32-chars",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/finance_db"
    db_echo: bool = False                 # log every SQL statement (noisy; opt-in)
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # JWT
    jwt_secret: str = "change-this-secret"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    # Login brute-force protection
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Receipts
    upload_dir: Path = Path("uploads")
    max_receipt_mb: int = 10

    # App
    frontend_url: str = "http://localhost:3000"
    # Extra allowed CORS origins, comma separated (frontend_url is always allowed)
    cors_extra_origins: str = ""
    environment: str = "development"
    app_name: str = "Finance Management System"
    app_version: str = "1.1.0"
    api_prefix: str = "/api/v1"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        extra = [o.strip() for o in self.cors_extra_origins.split(",") if o.strip()]
        return [self.frontend_url, *extra]

    @property
    def max_receipt_bytes(self) -> int:
        return self.max_receipt_mb * 1024 * 1024

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        # Fail fast instead of signing production tokens with a guessable key
        if self.is_production and (
            self.jwt_secret in _INSECURE_SECRETS or len(self.jwt_secret) < 32
        ):
            raise ValueError(
                "JWT_SECRET must be set to a random value of at least 32 characters in production"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
