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
    assert "APPLE_AUTH_AUDIENCE" in response.message
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
        apple_auth_audience="com.forgemind.app",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
    )

    response = validate_store_purchase("user-1", "apple", "valid-token")

    assert response.valid is False
    assert response.entitlement == "free"
    assert "purchase validation failed" in response.message


def test_production_storekit_validation_accepts_transaction(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        apple_auth_audience="com.forgemind.app",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
    )
    monkeypatch.setattr("app.services.subscription._build_storekit_bearer", lambda: "bearer")
    monkeypatch.setattr(
        "app.services.subscription._request_json",
        lambda *_, **__: {"signedTransactionInfo": "signed"},
    )

    response = validate_store_purchase("user-1", "apple", "transaction-id")

    assert response.valid is True
    assert response.entitlement == "premium"


def test_production_google_play_requires_product_id(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        google_play_package_name="com.forgemind",
        google_play_service_account_json='{"client_email":"service@example.com","private_key":"key"}',
    )

    response = validate_store_purchase("user-1", "google", "purchase-token")

    assert response.valid is False
    assert "product_id" in response.message


def test_production_google_play_validation_accepts_active_subscription(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        google_play_package_name="com.forgemind",
        google_play_service_account_json='{"client_email":"service@example.com","private_key":"key"}',
    )
    monkeypatch.setattr("app.services.subscription._fetch_google_access_token", lambda: "access-token")
    monkeypatch.setattr(
        "app.services.subscription._request_json",
        lambda *_, **__: {"paymentState": 1, "expiryTimeMillis": "4102444800000"},
    )

    response = validate_store_purchase("user-1", "google", "purchase-token", product_id="premium_monthly")

    assert response.valid is True
    assert response.entitlement == "premium"
