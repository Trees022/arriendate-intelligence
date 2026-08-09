from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SQLITE_URL = (
    f"sqlite+aiosqlite:///{(REPOSITORY_ROOT / '.local' / 'arriendate.db').as_posix()}"
)


class Settings(BaseSettings):
    """Validated server configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="ARRIENDATE_",
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Arriendate Intelligence API"
    environment: str = "development"
    database_url: str = DEFAULT_SQLITE_URL
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:5173", "http://localhost:5173"]
    )
    log_level: str = "INFO"
    seed_demo_data: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
