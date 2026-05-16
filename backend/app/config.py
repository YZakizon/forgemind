from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ForgeMind API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://forgemind:forgemind@localhost:5432/forgemind"
    jwt_secret: str = "dev-change-me"
    jwt_algorithm: str = "HS256"
    openai_api_key: str | None = None
    sentry_dsn: str | None = None
    posthog_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


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
