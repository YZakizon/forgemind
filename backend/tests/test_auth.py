from app.config import Settings, get_settings
from app.schemas import AuthProvider
import pytest

from app.services.auth import DEMO_USER_ID, extract_bearer_token, issue_access_token, verify_access_token, verify_identity_token


def override_settings(monkeypatch, **overrides):
    get_settings.cache_clear()
    settings = Settings(**overrides)
    monkeypatch.setattr("app.services.auth.get_settings", lambda: settings)
    return settings


def test_identity_token_stub_is_stable():
    first = verify_identity_token(AuthProvider.google, "valid-token")
    second = verify_identity_token(AuthProvider.google, "valid-token")
    assert first == second


def test_demo_identity_token_is_development_only(monkeypatch):
    override_settings(monkeypatch, environment="development")
    assert verify_identity_token(AuthProvider.google, "demo-token") == DEMO_USER_ID

    override_settings(monkeypatch, environment="production", google_auth_audience="forgemind")
    with pytest.raises(ValueError, match="disabled"):
        verify_identity_token(AuthProvider.google, "demo-token")


def test_production_google_auth_requires_audience(monkeypatch):
    override_settings(monkeypatch, environment="production")
    with pytest.raises(ValueError, match="Google auth audience"):
        verify_identity_token(AuthProvider.google, "valid-token")


def test_production_apple_auth_requires_audience(monkeypatch):
    override_settings(monkeypatch, environment="production")
    with pytest.raises(ValueError, match="Apple auth audience"):
        verify_identity_token(AuthProvider.apple, "valid-token")


def test_production_auth_fails_closed_when_configured(monkeypatch):
    override_settings(monkeypatch, environment="production", google_auth_audience="forgemind")
    with pytest.raises(ValueError, match="invalid"):
        verify_identity_token(AuthProvider.google, "valid-token")


def test_production_google_auth_verifies_oidc_subject(monkeypatch):
    override_settings(monkeypatch, environment="production", google_auth_audience="forgemind")
    monkeypatch.setattr(
        "app.services.auth._decode_oidc_token",
        lambda **_: {"sub": "google-user", "iss": "https://accounts.google.com"},
    )

    first = verify_identity_token(AuthProvider.google, "valid-token")
    second = verify_identity_token(AuthProvider.google, "valid-token")

    assert first == second
    assert first != DEMO_USER_ID


def test_production_google_auth_rejects_wrong_issuer(monkeypatch):
    override_settings(monkeypatch, environment="production", google_auth_audience="forgemind")
    monkeypatch.setattr(
        "app.services.auth._decode_oidc_token",
        lambda **_: {"sub": "google-user", "iss": "https://evil.example"},
    )

    with pytest.raises(ValueError, match="issuer"):
        verify_identity_token(AuthProvider.google, "valid-token")


def test_production_apple_auth_verifies_oidc_subject(monkeypatch):
    override_settings(monkeypatch, environment="production", apple_auth_audience="com.forgemind.app")
    monkeypatch.setattr(
        "app.services.auth._decode_oidc_token",
        lambda **_: {"sub": "apple-user", "iss": "https://appleid.apple.com"},
    )

    user_id = verify_identity_token(AuthProvider.apple, "valid-token")

    assert user_id != DEMO_USER_ID


def test_access_token_is_issued():
    token = issue_access_token("user-1")
    assert isinstance(token, str)
    assert token


def test_access_token_round_trip_returns_subject():
    token = issue_access_token("user-1")
    assert verify_access_token(token) == "user-1"


def test_bearer_token_extraction_rejects_missing_scheme():
    with pytest.raises(ValueError):
        extract_bearer_token("Basic abc")
