from datetime import UTC, datetime, timedelta
from uuid import uuid5, NAMESPACE_URL
import jwt
from jwt import InvalidTokenError, PyJWKClient
from app.config import get_settings
from app.schemas import AuthProvider

DEMO_USER_ID = "00000000-0000-4000-8000-000000000001"
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def verify_identity_token(provider: AuthProvider, identity_token: str) -> str:
    if not identity_token or len(identity_token) < 8:
        raise ValueError("identity token is invalid")
    settings = get_settings()
    production = settings.environment.lower() == "production"
    if identity_token == "demo-token":
        if production:
            raise ValueError("demo identity token is disabled in production")
        return DEMO_USER_ID
    if production:
        _require_provider_config(provider)
        return _verify_provider_identity_token(provider, identity_token)
    return str(uuid5(NAMESPACE_URL, f"{provider}:{identity_token}"))


def _require_provider_config(provider: AuthProvider) -> None:
    settings = get_settings()
    if provider == AuthProvider.google and not settings.google_auth_audience:
        raise ValueError("Google auth audience is not configured")
    if provider == AuthProvider.apple and not settings.apple_auth_audience:
        raise ValueError("Apple auth audience is not configured")


def _verify_provider_identity_token(provider: AuthProvider, identity_token: str) -> str:
    settings = get_settings()
    try:
        if provider == AuthProvider.google:
            claims = _decode_oidc_token(
                identity_token=identity_token,
                jwks_url=GOOGLE_JWKS_URL,
                audience=settings.google_auth_audience or "",
                issuer=None,
            )
            issuer = claims.get("iss")
            if issuer not in GOOGLE_ISSUERS:
                raise ValueError("Google identity token issuer is invalid")
        else:
            claims = _decode_oidc_token(
                identity_token=identity_token,
                jwks_url=APPLE_JWKS_URL,
                audience=settings.apple_auth_audience or "",
                issuer=settings.apple_auth_issuer,
            )
    except InvalidTokenError as exc:
        raise ValueError(f"{provider.value} identity token is invalid") from exc
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"{provider.value} identity token is invalid") from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError(f"{provider.value} identity token is missing subject")
    return str(uuid5(NAMESPACE_URL, f"{provider}:{subject}"))


def _decode_oidc_token(identity_token: str, jwks_url: str, audience: str, issuer: str | None) -> dict:
    signing_key = PyJWKClient(jwks_url).get_signing_key_from_jwt(identity_token)
    options = {"verify_iss": issuer is not None}
    return jwt.decode(
        identity_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
        options=options,
    )


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
