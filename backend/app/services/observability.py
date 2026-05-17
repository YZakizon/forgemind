from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import get_settings


@lru_cache
def configure_observability() -> None:
    settings = get_settings()
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.05,
            )
        except Exception:
            pass
    if settings.posthog_api_key:
        try:
            from posthog import Posthog

            Posthog(project_api_key=settings.posthog_api_key, host=settings.posthog_host)
        except Exception:
            pass


def capture_event(event: str, properties: dict[str, Any] | None = None) -> None:
    settings = get_settings()
    if not settings.posthog_api_key:
        return
    try:
        from posthog import Posthog

        Posthog(project_api_key=settings.posthog_api_key, host=settings.posthog_host).capture(
            distinct_id=properties.get("user_id", "system") if properties else "system",
            event=event,
            properties=properties or {},
        )
    except Exception:
        return
