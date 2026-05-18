from app.config import Settings, get_settings
from app.services.subscription import validate_store_purchase


def override_subscription_settings(monkeypatch, **overrides):
    get_settings.cache_clear()
    settings = Settings(**overrides)
    monkeypatch.setattr("app.services.subscription.get_settings", lambda: settings)
    return settings


def test_subscription_dev_stub_accepts_valid_platform_token(monkeypatch):
    override_subscription_settings(monkeypatch, environment="development")

    response = validate_store_purchase("user-1", "apple", "valid-token")

    assert response.valid is True
    assert response.entitlement == "premium"
    assert "development stub" in response.message


def test_subscription_rejects_unsupported_platform(monkeypatch):
    override_subscription_settings(monkeypatch, environment="development")

    response = validate_store_purchase("user-1", "stripe", "valid-token")

    assert response.valid is False
    assert response.entitlement == "free"
    assert "Unsupported" in response.message


def test_production_storekit_requires_credentials(monkeypatch):
    override_subscription_settings(monkeypatch, environment="production")

    response = validate_store_purchase("user-1", "apple", "valid-token")

    assert response.valid is False
    assert "STOREKIT_ISSUER_ID" in response.message
    assert "STOREKIT_KEY_ID" in response.message
    assert "STOREKIT_PRIVATE_KEY" in response.message


def test_production_google_play_requires_credentials(monkeypatch):
    override_subscription_settings(monkeypatch, environment="production")

    response = validate_store_purchase("user-1", "google", "valid-token")

    assert response.valid is False
    assert "GOOGLE_PLAY_PACKAGE_NAME" in response.message
    assert "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON" in response.message


def test_production_subscription_boundary_fails_closed_when_configured(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
    )

    response = validate_store_purchase("user-1", "apple", "valid-token")

    assert response.valid is False
    assert response.entitlement == "free"
    assert "real store verification is not implemented" in response.message
