from app.schemas import SubscriptionValidationResponse


def validate_store_purchase(user_id: str, platform: str, purchase_token: str) -> SubscriptionValidationResponse:
    # TODO: Verify StoreKit and Google Play Billing server-side with platform credentials.
    normalized = platform.lower()
    valid_platform = normalized in {"apple", "google"}
    valid = valid_platform and len(purchase_token) >= 8
    return SubscriptionValidationResponse(
        user_id=user_id,
        platform=normalized,
        valid=valid,
        entitlement="premium" if valid else "free",
        message="Validated with local MVP stub. Configure platform credentials before production use.",
    )
