from app.config import get_settings
from app.schemas import SubscriptionValidationResponse


def validate_store_purchase(user_id: str, platform: str, purchase_token: str) -> SubscriptionValidationResponse:
    normalized = platform.lower()
    valid_platform = normalized in {"apple", "google"}
    if not valid_platform:
        return SubscriptionValidationResponse(
            user_id=user_id,
            platform=normalized,
            valid=False,
            entitlement="free",
            message="Unsupported store platform.",
        )

    settings = get_settings()
    production = settings.environment.lower() == "production"
    if production:
        missing = _missing_platform_config(normalized)
        if missing:
            return SubscriptionValidationResponse(
                user_id=user_id,
                platform=normalized,
                valid=False,
                entitlement="free",
                message=f"{normalized} purchase validation is not configured: {', '.join(missing)}.",
            )
        return SubscriptionValidationResponse(
            user_id=user_id,
            platform=normalized,
            valid=False,
            entitlement="free",
            message=f"{normalized} purchase validation is configured but real store verification is not implemented.",
        )

    valid = valid_platform and len(purchase_token) >= 8
    return SubscriptionValidationResponse(
        user_id=user_id,
        platform=normalized,
        valid=valid,
        entitlement="premium" if valid else "free",
        message="Validated with local development stub. Configure platform credentials before production use.",
    )


def _missing_platform_config(platform: str) -> list[str]:
    settings = get_settings()
    if platform == "apple":
        required = {
            "STOREKIT_ISSUER_ID": settings.storekit_issuer_id,
            "STOREKIT_KEY_ID": settings.storekit_key_id,
            "STOREKIT_PRIVATE_KEY": settings.storekit_private_key,
        }
    else:
        required = {
            "GOOGLE_PLAY_PACKAGE_NAME": settings.google_play_package_name,
            "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON": settings.google_play_service_account_json,
        }
    return [name for name, value in required.items() if not value]
