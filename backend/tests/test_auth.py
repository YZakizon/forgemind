from app.schemas import AuthProvider
from app.services.auth import issue_access_token, verify_identity_token


def test_identity_token_stub_is_stable():
    first = verify_identity_token(AuthProvider.google, "valid-token")
    second = verify_identity_token(AuthProvider.google, "valid-token")
    assert first == second


def test_access_token_is_issued():
    token = issue_access_token("user-1")
    assert isinstance(token, str)
    assert token
