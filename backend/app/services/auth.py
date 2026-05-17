from datetime import UTC, datetime, timedelta
from uuid import uuid5, NAMESPACE_URL
import jwt
from jwt import InvalidTokenError
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


def verify_access_token(access_token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            access_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="forgemind",
        )
    except InvalidTokenError as exc:
        raise ValueError("access token is invalid") from exc
    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise ValueError("access token is invalid")
    return user_id


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise ValueError("missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ValueError("authorization header must be Bearer token")
    return token
