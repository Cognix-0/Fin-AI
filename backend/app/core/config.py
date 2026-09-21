from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/finance_db"

    # JWT
    jwt_secret: str = "change-this-secret"
    jwt_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    # App
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"
    app_name: str = "Finance Management System"
    api_prefix: str = "/api/v1"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
