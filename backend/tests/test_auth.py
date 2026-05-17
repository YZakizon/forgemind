from app.schemas import AuthProvider
import pytest

from app.services.auth import extract_bearer_token, issue_access_token, verify_access_token, verify_identity_token


def test_identity_token_stub_is_stable():
    first = verify_identity_token(AuthProvider.google, "valid-token")
    second = verify_identity_token(AuthProvider.google, "valid-token")
    assert first == second


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
