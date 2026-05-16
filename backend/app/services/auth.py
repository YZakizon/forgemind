from datetime import UTC, datetime, timedelta
from uuid import uuid5, NAMESPACE_URL
import jwt
from app.config import get_settings
from app.schemas import AuthProvider


def verify_identity_token(provider: AuthProvider, identity_token: str) -> str:
    # TODO: Replace this local verifier with Google and Apple public-key validation in production.
    if not identity_token or len(identity_token) < 8:
        raise ValueError("identity token is invalid")
    return str(uuid5(NAMESPACE_URL, f"{provider}:{identity_token}"))


def issue_access_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=12),
        "iss": "forgemind",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
