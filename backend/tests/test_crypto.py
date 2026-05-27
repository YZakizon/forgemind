import pytest

from app.config import Settings
from app.services.crypto import (
    decrypt_text_for_user,
    encrypt_text_for_user,
    generate_dek,
    hash_plaintext,
    normalize_master_key,
    unwrap_dek,
    wrap_dek,
)


def test_dek_wrap_round_trip_with_env_master_key():
    settings = Settings(encryption_master_key="test-master-key", encryption_key_id="test-v1")
    user_id = "00000000-0000-4000-8000-000000000001"
    dek = generate_dek()

    wrapped, nonce, key_id = wrap_dek(dek, user_id, settings)

    assert key_id == "test-v1"
    assert unwrap_dek(wrapped, nonce, user_id, key_id, settings) == dek


def test_text_encryption_requires_matching_aad():
    user_id = "00000000-0000-4000-8000-000000000001"
    dek = generate_dek()
    encrypted = encrypt_text_for_user(user_id, "profile_facts", "value", "bikes every weekend", dek, "test-v1")

    assert decrypt_text_for_user(user_id, "profile_facts", "value", encrypted.ciphertext, encrypted.nonce, dek) == "bikes every weekend"
    with pytest.raises(Exception):
        decrypt_text_for_user(user_id, "memories", "content", encrypted.ciphertext, encrypted.nonce, dek)


def test_plaintext_hash_is_stable_and_context_bound():
    user_id = "00000000-0000-4000-8000-000000000001"
    settings = Settings(encryption_master_key="test-master-key")

    first = hash_plaintext(user_id, "profile_facts", "value", "direct", settings)
    second = hash_plaintext(user_id, "profile_facts", "value", "direct", settings)
    other = hash_plaintext(user_id, "memories", "content", "direct", settings)

    assert first == second
    assert first != other


def test_production_requires_master_key():
    settings = Settings(environment="production", encryption_master_key=None)

    with pytest.raises(RuntimeError, match="ENCRYPTION_MASTER_KEY"):
        normalize_master_key(settings=settings)
