"""Application settings, loaded from environment variables via pydantic-settings."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to backend/.env so it loads regardless of the process CWD
# (config.py lives at backend/app/core/, so two parents up is backend/).
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), extra="ignore", case_sensitive=False)

    # --- Database ---
    database_url: str = "postgresql+asyncpg://csp:csp_password@localhost:5432/csp"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth / JWT ---
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- AI (any OpenAI-compatible provider: OpenRouter, Google Gemini, OpenAI) ---
    ai_api_key: str = ""
    ai_model: str = "openai/gpt-4o-mini"
    ai_base_url: str = "https://openrouter.ai/api/v1"

    # --- App ---
    cors_origins: str = "http://localhost:3000"
    dashboard_cache_ttl_seconds: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS is a comma-separated string in env; expose it as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
