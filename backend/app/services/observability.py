from __future__ import annotations

from functools import lru_cache
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger("forgemind.observability")


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
            logger.exception("Sentry initialization failed")
    if settings.posthog_api_key:
        try:
            _posthog_client()
        except Exception:
            logger.exception("PostHog initialization failed")


def capture_event(event: str, properties: dict[str, Any] | None = None) -> None:
    settings = get_settings()
    if not settings.posthog_api_key:
        return
    try:
        _posthog_client().capture(
            distinct_id=properties.get("user_id", "system") if properties else "system",
            event=event,
            properties=properties or {},
        )
    except Exception:
        logger.exception("PostHog capture failed", extra={"event": event})
        return


@lru_cache
def _posthog_client():
    settings = get_settings()
    from posthog import Posthog

    return Posthog(project_api_key=settings.posthog_api_key or "", host=settings.posthog_host)
