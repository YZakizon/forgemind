from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    app_name: str = "ForgeMind API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://forgemind:forgemind@localhost:5435/forgemind"
    jwt_secret: str = "dev-change-me"
    jwt_algorithm: str = "HS256"
    encryption_provider: str = "local"
    encryption_master_key: str | None = None
    encryption_key_id: str = "local-v1"
    ai_provider: str = "openai"
    stt_provider: str = "openai"
    tts_provider: str = "openai"
    google_auth_audience: str | None = None
    apple_auth_audience: str | None = None
    apple_auth_issuer: str = "https://appleid.apple.com"
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_transcription_model: str = "whisper-1"
    openai_stt_model: str | None = None
    openai_stt_language: str | None = None
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "cedar"
    openai_tts_response_format: str = "aac"
    openai_tts_speed: float = 0.95
    openai_tts_instructions: str = (
        "Voice: calm, grounded, warm, and conversational. Speak like a continuous private conversation, "
        "not a scripted prompt. Use natural pacing, slight variation in emphasis, and a steady supportive tone. "
        "Avoid sounding robotic, flat, overly cheerful, or like every line is a separate question."
    )
    deepgram_api_key: str | None = None
    deepgram_tts_model: str = "aura-2-thalia-en"
    deepgram_tts_encoding: str = "mp3"
    deepgram_tts_container: str | None = None
    deepgram_tts_sample_rate: int | None = None
    deepgram_tts_bitrate: int | None = None
    deepgram_tts_speed: float = 1.0
    deepgram_tts_base_url: str = "https://api.deepgram.com/v1/speak"
    sentry_dsn: str | None = None
    posthog_api_key: str | None = None
    posthog_host: str = "https://app.posthog.com"
    storekit_issuer_id: str | None = None
    storekit_key_id: str | None = None
    storekit_private_key: str | None = None
    storekit_root_ca_pem: str | None = None
    storekit_api_base_url: str = "https://api.storekit.itunes.apple.com"
    google_play_package_name: str | None = None
    google_play_service_account_json: str | None = None

    @field_validator(
        "openai_stt_language",
        "encryption_master_key",
        "deepgram_api_key",
        "deepgram_tts_container",
        "sentry_dsn",
        "posthog_api_key",
        "storekit_issuer_id",
        "storekit_key_id",
        "storekit_private_key",
        "storekit_root_ca_pem",
        "google_play_package_name",
        "google_play_service_account_json",
        mode="before",
    )
    @classmethod
    def blank_string_to_none(cls, value):
        return None if value == "" else value

    @field_validator("deepgram_tts_sample_rate", "deepgram_tts_bitrate", mode="before")
    @classmethod
    def blank_int_to_none(cls, value):
        return None if value == "" else value

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
    stt_enabled: bool
    tts_enabled: bool
    tts_provider: str
    tts_model: str
    tts_voice: str
    tts_response_format: str
    sentry_enabled: bool
    posthog_enabled: bool


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_public_config() -> PublicConfig:
    settings = get_settings()
    deepgram_tts_enabled = bool(settings.deepgram_api_key and settings.tts_provider == "deepgram")
    openai_tts_enabled = bool(settings.openai_api_key and settings.tts_provider == "openai")
    return PublicConfig(
        app_name=settings.app_name,
        environment=settings.environment,
        ai_enabled=bool(settings.openai_api_key),
        stt_enabled=bool(settings.openai_api_key and settings.stt_provider == "openai"),
        tts_enabled=openai_tts_enabled or deepgram_tts_enabled,
        tts_provider=settings.tts_provider,
        tts_model=settings.deepgram_tts_model if settings.tts_provider == "deepgram" else settings.openai_tts_model,
        tts_voice=settings.deepgram_tts_model if settings.tts_provider == "deepgram" else settings.openai_tts_voice,
        tts_response_format=settings.deepgram_tts_encoding if settings.tts_provider == "deepgram" else settings.openai_tts_response_format,
        sentry_enabled=bool(settings.sentry_dsn),
        posthog_enabled=bool(settings.posthog_api_key),
    )
