from __future__ import annotations

import base64
import json
import time
from typing import Any
from urllib import parse, request

import jwt
from cryptography import x509

from app.config import get_settings
from app.schemas import SubscriptionValidationResponse


def validate_store_purchase(
    user_id: str,
    platform: str,
    purchase_token: str,
    product_id: str | None = None,
) -> SubscriptionValidationResponse:
    normalized = platform.lower()
    valid_platform = normalized in {"apple", "google"}
    if not valid_platform:
        return SubscriptionValidationResponse(
            user_id=user_id,
            platform=normalized,
            valid=False,
            entitlement="free",
            message="Unsupported store platform.",
        )

    settings = get_settings()
    production = settings.environment.lower() == "production"
    if production:
        missing = _missing_platform_config(normalized)
        if not product_id:
            missing.append("product_id")
        if missing:
            return SubscriptionValidationResponse(
                user_id=user_id,
                platform=normalized,
                valid=False,
                entitlement="free",
                message=f"{normalized} purchase validation is not configured: {', '.join(missing)}.",
            )
        return _validate_production_purchase(user_id, normalized, purchase_token, product_id)

    valid = valid_platform and len(purchase_token) >= 8
    return SubscriptionValidationResponse(
        user_id=user_id,
        platform=normalized,
        valid=valid,
        entitlement="premium" if valid else "free",
        message="Validated with local development stub. Configure platform credentials before production use.",
    )


def _missing_platform_config(platform: str) -> list[str]:
    settings = get_settings()
    if platform == "apple":
        required = {
            "APPLE_AUTH_AUDIENCE": settings.apple_auth_audience,
            "STOREKIT_ISSUER_ID": settings.storekit_issuer_id,
            "STOREKIT_KEY_ID": settings.storekit_key_id,
            "STOREKIT_PRIVATE_KEY": settings.storekit_private_key,
        }
    else:
        required = {
            "GOOGLE_PLAY_PACKAGE_NAME": settings.google_play_package_name,
            "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON": settings.google_play_service_account_json,
        }
    return [name for name, value in required.items() if not value]


def _validate_production_purchase(
    user_id: str,
    platform: str,
    purchase_token: str,
    product_id: str | None,
) -> SubscriptionValidationResponse:
    try:
        if platform == "apple":
            valid = _validate_storekit_transaction(purchase_token, product_id or "")
        else:
            valid = _validate_google_play_subscription(purchase_token, product_id or "")
    except Exception as exc:
        return SubscriptionValidationResponse(
            user_id=user_id,
            platform=platform,
            valid=False,
            entitlement="free",
            message=f"{platform} purchase validation failed: {exc}",
        )

    return SubscriptionValidationResponse(
        user_id=user_id,
        platform=platform,
        valid=valid,
        entitlement="premium" if valid else "free",
        message=f"{platform} purchase validation completed.",
    )


def _validate_storekit_transaction(transaction_id: str, product_id: str) -> bool:
    settings = get_settings()
    bearer = _build_storekit_bearer()
    base_url = settings.storekit_api_base_url.rstrip("/")
    payload = _request_json(
        f"{base_url}/inApps/v1/transactions/{parse.quote(transaction_id)}",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    signed_transaction = payload.get("signedTransactionInfo")
    if not isinstance(signed_transaction, str) or not signed_transaction:
        return False
    claims = _decode_storekit_signed_transaction(signed_transaction)
    return _storekit_claims_are_active(claims, product_id)


def _decode_storekit_signed_transaction(signed_transaction: str) -> dict[str, Any]:
    header = jwt.get_unverified_header(signed_transaction)
    certificate_chain = header.get("x5c")
    if not isinstance(certificate_chain, list) or not certificate_chain:
        raise RuntimeError("StoreKit signed transaction is missing certificate chain")
    leaf_certificate = x509.load_der_x509_certificate(base64.b64decode(certificate_chain[0]))
    return jwt.decode(
        signed_transaction,
        leaf_certificate.public_key(),
        options={
            "verify_aud": False,
            "verify_exp": False,
        },
        algorithms=["ES256"],
    )


def _storekit_claims_are_active(claims: dict[str, Any], product_id: str) -> bool:
    settings = get_settings()
    if claims.get("bundleId") != settings.apple_auth_audience:
        return False
    if claims.get("productId") != product_id:
        return False
    if claims.get("revocationDate"):
        return False
    expires_date = _int_or_zero(claims.get("expiresDate"))
    if expires_date <= int(time.time() * 1000):
        return False
    return True


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _validate_google_play_subscription(purchase_token: str, product_id: str) -> bool:
    settings = get_settings()
    access_token = _fetch_google_access_token()
    package_name = parse.quote(settings.google_play_package_name or "", safe="")
    subscription_id = parse.quote(product_id, safe="")
    token = parse.quote(purchase_token, safe="")
    payload = _request_json(
        "https://androidpublisher.googleapis.com/androidpublisher/v3/"
        f"applications/{package_name}/purchases/subscriptions/{subscription_id}/tokens/{token}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    payment_state = payload.get("paymentState")
    expiry_time = int(payload.get("expiryTimeMillis") or "0")
    return payment_state in {1, 2} and expiry_time > int(time.time() * 1000)


def _build_storekit_bearer() -> str:
    settings = get_settings()
    now = int(time.time())
    return jwt.encode(
        {
            "iss": settings.storekit_issuer_id,
            "iat": now,
            "exp": now + 900,
            "aud": "appstoreconnect-v1",
            "bid": settings.apple_auth_audience,
        },
        (settings.storekit_private_key or "").replace("\\n", "\n"),
        algorithm="ES256",
        headers={"kid": settings.storekit_key_id, "typ": "JWT"},
    )


def _fetch_google_access_token() -> str:
    settings = get_settings()
    service_account = json.loads(settings.google_play_service_account_json or "{}")
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": service_account["client_email"],
            "scope": "https://www.googleapis.com/auth/androidpublisher",
            "aud": service_account.get("token_uri", "https://oauth2.googleapis.com/token"),
            "iat": now,
            "exp": now + 3600,
        },
        service_account["private_key"],
        algorithm="RS256",
    )
    token_payload = _request_json(
        service_account.get("token_uri", "https://oauth2.googleapis.com/token"),
        method="POST",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    access_token = token_payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise RuntimeError("Google OAuth token response did not include access_token")
    return access_token


def _request_json(
    url: str,
    method: str = "GET",
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = parse.urlencode(data).encode("utf-8") if data else None
    req = request.Request(url, data=body, headers=headers or {}, method=method)
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))
