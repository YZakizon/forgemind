from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import Settings, get_settings

DEK_BYTES = 32
NONCE_BYTES = 12


@dataclass(frozen=True)
class EncryptedText:
    ciphertext: bytes
    nonce: bytes
    key_id: str
    value_hash: str


def generate_dek() -> bytes:
    return os.urandom(DEK_BYTES)


def aad_for_user_dek(user_id: str, key_id: str) -> bytes:
    return f"forgemind:user-dek:{user_id}:{key_id}".encode("utf-8")


def aad_for_field(user_id: str, table: str, field: str) -> bytes:
    return f"forgemind:{table}:{field}:{user_id}".encode("utf-8")


def normalize_master_key(value: str | None = None, settings: Settings | None = None) -> bytes:
    settings = settings or get_settings()
    configured = value if value is not None else settings.encryption_master_key
    if not configured:
        if settings.environment.lower() in {"production", "prod"}:
            raise RuntimeError("ENCRYPTION_MASTER_KEY is required in production")
        return hashlib.sha256(b"forgemind-development-encryption-key").digest()

    try:
        decoded = base64.urlsafe_b64decode(configured + "=" * (-len(configured) % 4))
        if len(decoded) == DEK_BYTES:
            return decoded
    except Exception:
        pass
    raw = configured.encode("utf-8")
    return raw if len(raw) == DEK_BYTES else hashlib.sha256(raw).digest()


def wrap_dek(dek: bytes, user_id: str, settings: Settings | None = None) -> tuple[bytes, bytes, str]:
    settings = settings or get_settings()
    key_id = settings.encryption_key_id
    nonce = os.urandom(NONCE_BYTES)
    wrapped = AESGCM(normalize_master_key(settings=settings)).encrypt(nonce, dek, aad_for_user_dek(user_id, key_id))
    return wrapped, nonce, key_id


def unwrap_dek(wrapped_dek: bytes, nonce: bytes, user_id: str, key_id: str, settings: Settings | None = None) -> bytes:
    return AESGCM(normalize_master_key(settings=settings)).decrypt(nonce, wrapped_dek, aad_for_user_dek(user_id, key_id))


def hash_plaintext(user_id: str, table: str, field: str, plaintext: str, settings: Settings | None = None) -> str:
    key = normalize_master_key(settings=settings)
    digest = hmac.new(key, aad_for_field(user_id, table, field) + b":" + plaintext.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def encrypt_text_for_user(user_id: str, table: str, field: str, plaintext: str, dek: bytes, key_id: str) -> EncryptedText:
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext.encode("utf-8"), aad_for_field(user_id, table, field))
    return EncryptedText(
        ciphertext=ciphertext,
        nonce=nonce,
        key_id=key_id,
        value_hash=hash_plaintext(user_id, table, field, plaintext),
    )


def decrypt_text_for_user(user_id: str, table: str, field: str, ciphertext: bytes, nonce: bytes, dek: bytes) -> str:
    plaintext = AESGCM(dek).decrypt(nonce, ciphertext, aad_for_field(user_id, table, field))
    return plaintext.decode("utf-8")
