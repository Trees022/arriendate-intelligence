from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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
    ai_provider: Literal["disabled", "openai_compatible"] = "disabled"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: SecretStr | None = None
    ai_chat_model: str = "gpt-5.6-luna"
    ai_reasoning_effort: Literal["none", "low", "medium", "high"] = "low"
    ai_timeout_seconds: float = Field(default=45, gt=0, le=300)
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_input_cost_per_million: Decimal | None = Field(default=None, ge=0)
    ai_output_cost_per_million: Decimal | None = Field(default=None, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
