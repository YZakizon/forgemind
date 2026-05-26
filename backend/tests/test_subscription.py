from datetime import UTC, datetime, timedelta
import time

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import Settings, get_settings
from app.services.subscription import validate_store_purchase, _verify_storekit_certificate_chain


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
    assert "STOREKIT_ROOT_CA_PEM" in response.message


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
        storekit_root_ca_pem="root",
    )

    response = validate_store_purchase("user-1", "apple", "valid-token")

    assert response.valid is False
    assert response.entitlement == "free"
    assert "product_id" in response.message


def test_production_storekit_validation_accepts_transaction(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        apple_auth_audience="com.forgemind.app",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
        storekit_root_ca_pem="root",
    )
    monkeypatch.setattr("app.services.subscription._build_storekit_bearer", lambda: "bearer")
    monkeypatch.setattr("app.services.subscription._decode_storekit_signed_transaction", lambda _: storekit_claims())
    monkeypatch.setattr(
        "app.services.subscription._request_json",
        lambda *_, **__: {"signedTransactionInfo": "signed-transaction"},
    )

    response = validate_store_purchase("user-1", "apple", "transaction-id", product_id="premium_monthly")

    assert response.valid is True
    assert response.entitlement == "premium"


def test_production_storekit_rejects_wrong_product(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        apple_auth_audience="com.forgemind.app",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
        storekit_root_ca_pem="root",
    )
    monkeypatch.setattr("app.services.subscription._build_storekit_bearer", lambda: "bearer")
    monkeypatch.setattr(
        "app.services.subscription._decode_storekit_signed_transaction",
        lambda _: storekit_claims(product_id="other_product"),
    )
    monkeypatch.setattr(
        "app.services.subscription._request_json",
        lambda *_, **__: {"signedTransactionInfo": "signed-transaction"},
    )

    response = validate_store_purchase("user-1", "apple", "transaction-id", product_id="premium_monthly")

    assert response.valid is False
    assert response.entitlement == "free"


def test_production_storekit_rejects_expired_transaction(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        apple_auth_audience="com.forgemind.app",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
        storekit_root_ca_pem="root",
    )
    monkeypatch.setattr("app.services.subscription._build_storekit_bearer", lambda: "bearer")
    monkeypatch.setattr(
        "app.services.subscription._decode_storekit_signed_transaction",
        lambda _: storekit_claims(expires_ms=int(time.time() * 1000) - 1000),
    )
    monkeypatch.setattr(
        "app.services.subscription._request_json",
        lambda *_, **__: {"signedTransactionInfo": "signed-transaction"},
    )

    response = validate_store_purchase("user-1", "apple", "transaction-id", product_id="premium_monthly")

    assert response.valid is False
    assert response.entitlement == "free"


def test_production_storekit_rejects_revoked_transaction(monkeypatch):
    override_subscription_settings(
        monkeypatch,
        environment="production",
        apple_auth_audience="com.forgemind.app",
        storekit_issuer_id="issuer",
        storekit_key_id="key",
        storekit_private_key="private",
        storekit_root_ca_pem="root",
    )
    monkeypatch.setattr("app.services.subscription._build_storekit_bearer", lambda: "bearer")
    monkeypatch.setattr(
        "app.services.subscription._decode_storekit_signed_transaction",
        lambda _: storekit_claims(revocation_ms=int(time.time() * 1000) - 1000),
    )
    monkeypatch.setattr(
        "app.services.subscription._request_json",
        lambda *_, **__: {"signedTransactionInfo": "signed-transaction"},
    )

    response = validate_store_purchase("user-1", "apple", "transaction-id", product_id="premium_monthly")

    assert response.valid is False
    assert response.entitlement == "free"


def test_storekit_certificate_chain_rejects_untrusted_root(monkeypatch):
    trusted_root, _trusted_key = make_certificate("Trusted Test Root")
    untrusted_root, untrusted_key = make_certificate("Untrusted Test Root")
    leaf, _leaf_key = make_certificate("StoreKit Leaf", issuer_cert=untrusted_root, issuer_key=untrusted_key)
    override_subscription_settings(
        monkeypatch,
        environment="production",
        storekit_root_ca_pem=trusted_root.public_bytes(serialization.Encoding.PEM).decode("utf-8"),
    )

    with pytest.raises(RuntimeError, match="root is not trusted"):
        _verify_storekit_certificate_chain([leaf, untrusted_root])


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


def storekit_claims(
    bundle_id: str = "com.forgemind.app",
    product_id: str = "premium_monthly",
    expires_ms: int | None = None,
    revocation_ms: int | None = None,
) -> dict:
    payload = {
        "bundleId": bundle_id,
        "productId": product_id,
        "expiresDate": expires_ms if expires_ms is not None else int(time.time() * 1000) + 86_400_000,
    }
    if revocation_ms is not None:
        payload["revocationDate"] = revocation_ms
    return payload


def make_certificate(
    common_name: str,
    issuer_cert: x509.Certificate | None = None,
    issuer_key: rsa.RSAPrivateKey | None = None,
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    issuer = issuer_cert.subject if issuer_cert else subject
    signer_key = issuer_key or key
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(signer_key, hashes.SHA256())
    )
    return cert, key
