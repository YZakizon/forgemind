from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    app_name: str = "ForgeMind API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://forgemind:forgemind@localhost:5432/forgemind"
    jwt_secret: str = "dev-change-me"
    jwt_algorithm: str = "HS256"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "whisper-1"
    sentry_dsn: str | None = None
    posthog_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=(
            BACKEND_ROOT / ".env",
            BACKEND_ROOT / ".env.local",
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


class PublicConfig(BaseModel):
    app_name: str
    environment: str
    ai_enabled: bool
    sentry_enabled: bool
    posthog_enabled: bool


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_public_config() -> PublicConfig:
    settings = get_settings()
    return PublicConfig(
        app_name=settings.app_name,
        environment=settings.environment,
        ai_enabled=bool(settings.openai_api_key),
        sentry_enabled=bool(settings.sentry_dsn),
        posthog_enabled=bool(settings.posthog_api_key),
    )
