from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from app.db import get_sessionmaker
from app.schemas import (
    GuidanceRule,
    MemoryCandidate,
    MemoryStatus,
    MoodCheckin,
    ProfileFact,
    ProfileFactPolicy,
    ProfileFactPolicyUpdate,
    ProgressSummary,
    ProgressTheme,
    ResetSession,
    SafetyEvent,
    SafetyLevel,
    UserDataExport,
)
from app.services.crypto import decrypt_text_for_user, encrypt_text_for_user, generate_dek, unwrap_dek, wrap_dek
from app.services.profile_facts import ExtractedProfileFact, normalize_profile_fact_policy
from app.services.guidance import DEFAULT_GUIDANCE_RULES


def _uuid(value: str) -> UUID:
    return UUID(value)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _is_missing_profile_facts_table(exc: Exception) -> bool:
    message = str(exc).lower()
    return "profile_facts" in message and (
        "undefinedtable" in message or "does not exist" in message or "no such table" in message
    )


def _is_missing_encryption_table(exc: Exception) -> bool:
    message = str(exc).lower()
    return "user_encryption_keys" in message and (
        "undefinedtable" in message or "does not exist" in message or "no such table" in message
    )


def _is_missing_profile_fact_policy_table(exc: Exception) -> bool:
    message = str(exc).lower()
    return "profile_fact_capture_policy" in message and (
        "undefinedtable" in message or "does not exist" in message or "no such table" in message
    )


def _row_value(row, key: str):
    try:
        return row[key]
    except Exception:
        return None


def _bytes(value) -> bytes:
    return bytes(value) if isinstance(value, memoryview) else value


def _json_value(value):
    return json.loads(value) if isinstance(value, str) else value


async def ensure_demo_user(user_id: str) -> None:
    parsed = _uuid(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO users (id, email, display_name, auth_provider, provider_subject)
                VALUES (:id, :email, 'Demo User', 'demo', :subject)
                ON CONFLICT (id) DO UPDATE SET updated_at = now()
                """
            ),
            {"id": parsed, "email": f"demo-{parsed}@forgemind.local", "subject": str(parsed)},
        )
        await session.commit()


async def upsert_user(
    user_id: str,
    email: str | None,
    display_name: str | None,
    provider: str,
    subject: str,
) -> None:
    parsed = _uuid(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO users (id, email, display_name, auth_provider, provider_subject)
                VALUES (:id, :email, :display_name, :provider, :subject)
                ON CONFLICT (id) DO UPDATE SET
                    email = COALESCE(EXCLUDED.email, users.email),
                    display_name = COALESCE(EXCLUDED.display_name, users.display_name),
                    auth_provider = EXCLUDED.auth_provider,
                    provider_subject = EXCLUDED.provider_subject,
                    updated_at = now()
                """
            ),
            {
                "id": parsed,
                "email": email,
                "display_name": display_name,
                "provider": provider,
                "subject": subject,
            },
        )
        await session.commit()


async def create_chat_session(user_id: str, mode: str) -> str:
    parsed_user_id = _uuid(user_id)
    session_id = uuid4()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO chat_sessions (id, user_id, mode)
                VALUES (:id, :user_id, :mode)
                """
            ),
            {"id": session_id, "user_id": parsed_user_id, "mode": mode},
        )
        await session.commit()
    return str(session_id)


async def save_chat_message(session_id: str, user_id: str, role: str, content: str, safety_level: SafetyLevel) -> str:
    message_id = uuid4()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO chat_messages (id, session_id, user_id, role, content, safety_level)
                VALUES (:id, :session_id, :user_id, :role, :content, :safety_level)
                """
            ),
            {
                "id": message_id,
                "session_id": _uuid(session_id),
                "user_id": _uuid(user_id),
                "role": role,
                "content": content,
                "safety_level": safety_level.value,
            },
        )
        await session.commit()
    return str(message_id)


async def log_safety_event(user_id: str, level: SafetyLevel, reasons: list[str], message_id: str | None = None) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO safety_events (id, user_id, message_id, level, reasons)
                VALUES (:id, :user_id, :message_id, :level, :reasons)
                """
            ),
            {
                "id": uuid4(),
                "user_id": _uuid(user_id),
                "message_id": _uuid(message_id) if message_id else None,
                "level": level.value,
                "reasons": reasons,
            },
        )
        await session.commit()


async def seed_default_guidance() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        for rule in DEFAULT_GUIDANCE_RULES:
            await session.execute(
                text(
                    """
                    INSERT INTO guidance_rules (
                        id, topic, tags, goal, do_rules, avoid_rules, tone,
                        safety_level, priority, approved_by, active
                    )
                    VALUES (
                        :id, :topic, :tags, :goal, :do_rules, :avoid_rules, :tone,
                        :safety_level, :priority, :approved_by, :active
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        topic = EXCLUDED.topic,
                        tags = EXCLUDED.tags,
                        goal = EXCLUDED.goal,
                        do_rules = EXCLUDED.do_rules,
                        avoid_rules = EXCLUDED.avoid_rules,
                        tone = EXCLUDED.tone,
                        safety_level = EXCLUDED.safety_level,
                        priority = EXCLUDED.priority,
                        approved_by = EXCLUDED.approved_by,
                        active = EXCLUDED.active,
                        updated_at = now()
                    """
                ),
                {
                    "id": _stable_rule_uuid(rule.id),
                    "topic": rule.topic,
                    "tags": rule.tags,
                    "goal": rule.goal,
                    "do_rules": rule.do_rules,
                    "avoid_rules": rule.avoid_rules,
                    "tone": rule.tone,
                    "safety_level": rule.safety_level.value,
                    "priority": rule.priority,
                    "approved_by": rule.approved_by,
                    "active": rule.active,
                },
            )
        await session.commit()


async def fetch_guidance_rules() -> list[GuidanceRule]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, topic, tags, goal, do_rules, avoid_rules, tone, safety_level,
                           priority, approved_by, active
                    FROM guidance_rules
                    WHERE active = true
                    ORDER BY priority DESC, updated_at DESC
                    """
                )
            )
        ).mappings())
    return [
        GuidanceRule(
            id=str(row["id"]),
            topic=row["topic"],
            tags=list(row["tags"] or []),
            goal=row["goal"],
            do_rules=list(row["do_rules"] or []),
            avoid_rules=list(row["avoid_rules"] or []),
            tone=row["tone"],
            safety_level=SafetyLevel(row["safety_level"]),
            priority=row["priority"],
            approved_by=row["approved_by"],
            active=row["active"],
        )
        for row in rows
    ]


async def retrieve_memory_candidates(user_id: str, embedding: list[float], limit: int = 20) -> list[MemoryCandidate]:
    dek = await get_user_dek(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, type, content, content_ciphertext, content_nonce, content_key_id,
                           status, importance, confidence, unsafe,
                           created_at, updated_at, archived_at, expires_at,
                           GREATEST(0.0, 1.0 - (embedding <=> CAST(:embedding AS vector))) AS similarity
                    FROM memories
                    WHERE user_id = :user_id
                      AND status = 'active'
                      AND embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :limit
                    """
                ),
                {"user_id": _uuid(user_id), "embedding": _vector_literal(embedding), "limit": limit},
            )
        ).mappings())
    return [_memory_from_row(row, dek=dek) for row in rows]


async def insert_memories(user_id: str, contents: list[str], embedding_by_content: dict[str, list[float]]) -> None:
    if not contents:
        return
    dek, key_id = await get_or_create_user_dek(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        for content in contents:
            encrypted = encrypt_text_for_user(user_id, "memories", "content", content, dek, key_id)
            await session.execute(
                text(
                    """
                    INSERT INTO memories (
                        id, user_id, type, content, content_ciphertext, content_nonce, content_key_id, content_hash,
                        status, importance, confidence, unsafe, embedding
                    )
                    VALUES (
                        :id, :user_id, 'emotional_pattern', '', :content_ciphertext, :content_nonce, :content_key_id,
                        :content_hash, 'active', 0.55, 0.65, false, CAST(:embedding AS vector)
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "user_id": _uuid(user_id),
                    "content_ciphertext": encrypted.ciphertext,
                    "content_nonce": encrypted.nonce,
                    "content_key_id": encrypted.key_id,
                    "content_hash": encrypted.value_hash,
                    "embedding": _vector_literal(embedding_by_content[content]),
                },
            )
        await session.commit()


async def get_user_dek(user_id: str) -> tuple[bytes, str] | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT wrapped_dek, wrap_nonce, wrap_key_id
                        FROM user_encryption_keys
                        WHERE user_id = :user_id
                        """
                    ),
                    {"user_id": _uuid(user_id)},
                )
            ).mappings().one_or_none()
        except Exception as exc:
            if _is_missing_encryption_table(exc):
                return None
            raise
    if row is None:
        return None
    key_id = row["wrap_key_id"]
    return unwrap_dek(_bytes(row["wrapped_dek"]), _bytes(row["wrap_nonce"]), user_id, key_id), key_id


async def get_or_create_user_dek(user_id: str) -> tuple[bytes, str]:
    existing = await get_user_dek(user_id)
    if existing is not None:
        return existing
    await ensure_demo_user(user_id)
    dek = generate_dek()
    wrapped_dek, wrap_nonce, key_id = wrap_dek(dek, user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO user_encryption_keys (user_id, wrapped_dek, wrap_nonce, wrap_key_id)
                    VALUES (:user_id, :wrapped_dek, :wrap_nonce, :wrap_key_id)
                    ON CONFLICT (user_id) DO NOTHING
                    RETURNING wrapped_dek, wrap_nonce, wrap_key_id
                    """
                ),
                {
                    "user_id": _uuid(user_id),
                    "wrapped_dek": wrapped_dek,
                    "wrap_nonce": wrap_nonce,
                    "wrap_key_id": key_id,
                },
            )
        ).mappings().one_or_none()
        await session.commit()
    if row is None:
        existing = await get_user_dek(user_id)
        if existing is None:
            raise RuntimeError("user encryption key was not created")
        return existing
    return unwrap_dek(_bytes(row["wrapped_dek"]), _bytes(row["wrap_nonce"]), user_id, row["wrap_key_id"]), row["wrap_key_id"]


async def backfill_encrypted_sensitive_text(limit: int = 500) -> dict[str, int]:
    memory_count = await _backfill_memory_content(limit)
    profile_fact_count = await _backfill_profile_fact_values(limit)
    return {"memories": memory_count, "profile_facts": profile_fact_count}


async def _backfill_memory_content(limit: int) -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, content
                    FROM memories
                    WHERE content_ciphertext IS NULL AND content <> ''
                    ORDER BY created_at ASC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings())

    for row in rows:
        user_id = str(row["user_id"])
        dek, key_id = await get_or_create_user_dek(user_id)
        encrypted = encrypt_text_for_user(user_id, "memories", "content", row["content"], dek, key_id)
        async with sessionmaker() as session:
            await session.execute(
                text(
                    """
                    UPDATE memories
                    SET content = '',
                        content_ciphertext = :ciphertext,
                        content_nonce = :nonce,
                        content_key_id = :key_id,
                        content_hash = :content_hash,
                        updated_at = now()
                    WHERE id = :id AND content_ciphertext IS NULL
                    """
                ),
                {
                    "id": row["id"],
                    "ciphertext": encrypted.ciphertext,
                    "nonce": encrypted.nonce,
                    "key_id": encrypted.key_id,
                    "content_hash": encrypted.value_hash,
                },
            )
            await session.commit()
    return len(rows)


async def _backfill_profile_fact_values(limit: int) -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, value
                    FROM profile_facts
                    WHERE value_ciphertext IS NULL AND value <> ''
                    ORDER BY created_at ASC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings())

    for row in rows:
        user_id = str(row["user_id"])
        dek, key_id = await get_or_create_user_dek(user_id)
        encrypted = encrypt_text_for_user(user_id, "profile_facts", "value", row["value"], dek, key_id)
        async with sessionmaker() as session:
            await session.execute(
                text(
                    """
                    UPDATE profile_facts
                    SET value = '',
                        value_ciphertext = :ciphertext,
                        value_nonce = :nonce,
                        value_key_id = :key_id,
                        value_hash = :value_hash,
                        updated_at = now()
                    WHERE id = :id AND value_ciphertext IS NULL
                    """
                ),
                {
                    "id": row["id"],
                    "ciphertext": encrypted.ciphertext,
                    "nonce": encrypted.nonce,
                    "key_id": encrypted.key_id,
                    "value_hash": encrypted.value_hash,
                },
            )
            await session.commit()
    return len(rows)


async def purge_expired_profile_facts(user_id: str | None = None) -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            if user_id:
                result = await session.execute(
                    text("DELETE FROM profile_facts WHERE user_id = :user_id AND expires_at <= now()"),
                    {"user_id": _uuid(user_id)},
                )
            else:
                result = await session.execute(text("DELETE FROM profile_facts WHERE expires_at <= now()"), {})
            await session.commit()
        except Exception as exc:
            if _is_missing_profile_facts_table(exc):
                return 0
            raise
    return int(result.rowcount or 0)


async def get_profile_fact_policy() -> ProfileFactPolicy:
    sessionmaker = get_sessionmaker()
    try:
        async with sessionmaker() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT capture_terms, blocked_terms, ttl_days_by_type
                        FROM profile_fact_capture_policy
                        WHERE id = 'default'
                        """
                    ),
                    {},
                )
            ).mappings().one_or_none()
    except Exception as exc:
        if _is_missing_profile_fact_policy_table(exc):
            return ProfileFactPolicy(**normalize_profile_fact_policy(None))
        raise
    if row is None:
        return ProfileFactPolicy(**normalize_profile_fact_policy(None))
    return ProfileFactPolicy(
        **normalize_profile_fact_policy(
            {
                "capture_terms": _json_value(row["capture_terms"]),
                "blocked_terms": _json_value(row["blocked_terms"]),
                "ttl_days_by_type": _json_value(row["ttl_days_by_type"]),
            }
        )
    )


async def save_profile_fact_policy(policy: ProfileFactPolicyUpdate) -> ProfileFactPolicy:
    normalized = normalize_profile_fact_policy(policy)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            row = (
                await session.execute(
                    text(
                        """
                        INSERT INTO profile_fact_capture_policy (
                            id, capture_terms, blocked_terms, ttl_days_by_type
                        )
                        VALUES (
                            'default',
                            CAST(:capture_terms AS jsonb),
                            CAST(:blocked_terms AS jsonb),
                            CAST(:ttl_days_by_type AS jsonb)
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            capture_terms = EXCLUDED.capture_terms,
                            blocked_terms = EXCLUDED.blocked_terms,
                            ttl_days_by_type = EXCLUDED.ttl_days_by_type,
                            updated_at = now()
                        RETURNING capture_terms, blocked_terms, ttl_days_by_type
                        """
                    ),
                    {
                        "capture_terms": json.dumps(normalized["capture_terms"]),
                        "blocked_terms": json.dumps(normalized["blocked_terms"]),
                        "ttl_days_by_type": json.dumps(normalized["ttl_days_by_type"]),
                    },
                )
            ).mappings().one()
            await session.commit()
        except Exception as exc:
            if _is_missing_profile_fact_policy_table(exc):
                return ProfileFactPolicy(**normalized)
            raise
    return ProfileFactPolicy(
        **normalize_profile_fact_policy(
            {
                "capture_terms": _json_value(row["capture_terms"]),
                "blocked_terms": _json_value(row["blocked_terms"]),
                "ttl_days_by_type": _json_value(row["ttl_days_by_type"]),
            }
        )
    )


async def insert_profile_facts(user_id: str, facts: list[ExtractedProfileFact]) -> None:
    if not facts:
        return
    await ensure_demo_user(user_id)
    await purge_expired_profile_facts(user_id)
    dek, key_id = await get_or_create_user_dek(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            for fact in facts:
                encrypted = encrypt_text_for_user(user_id, "profile_facts", "value", fact.value, dek, key_id)
                await session.execute(
                    text(
                        """
                        INSERT INTO profile_facts (
                            id, user_id, fact_type, label, value, value_ciphertext, value_nonce, value_key_id,
                            value_hash, sensitivity, source, confidence, expires_at
                        )
                        VALUES (
                            :id, :user_id, :fact_type, :label, '', :value_ciphertext, :value_nonce, :value_key_id,
                            :value_hash, :sensitivity, :source, :confidence, :expires_at
                        )
                        ON CONFLICT (user_id, fact_type, label, value_hash) WHERE value_hash IS NOT NULL DO UPDATE SET
                            sensitivity = EXCLUDED.sensitivity,
                            source = EXCLUDED.source,
                            confidence = GREATEST(profile_facts.confidence, EXCLUDED.confidence),
                            expires_at = GREATEST(profile_facts.expires_at, EXCLUDED.expires_at),
                            updated_at = now()
                        """
                    ),
                    {
                        "id": uuid4(),
                        "user_id": _uuid(user_id),
                        "fact_type": fact.fact_type,
                        "label": fact.label,
                        "value_ciphertext": encrypted.ciphertext,
                        "value_nonce": encrypted.nonce,
                        "value_key_id": encrypted.key_id,
                        "value_hash": encrypted.value_hash,
                        "sensitivity": fact.sensitivity,
                        "source": fact.source,
                        "confidence": fact.confidence,
                        "expires_at": fact.expires_at,
                    },
                )
            await session.commit()
        except Exception as exc:
            if _is_missing_profile_facts_table(exc):
                return
            raise


async def list_user_profile_facts(user_id: str) -> list[ProfileFact]:
    await purge_expired_profile_facts(user_id)
    dek = await get_user_dek(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            rows = list((
                await session.execute(
                    text(
                        """
                        SELECT id, user_id, fact_type, label, value, value_ciphertext, value_nonce, value_key_id,
                               sensitivity, source, confidence,
                               created_at, updated_at, expires_at
                        FROM profile_facts
                        WHERE user_id = :user_id AND expires_at > now()
                        ORDER BY updated_at DESC
                        LIMIT 100
                        """
                    ),
                    {"user_id": _uuid(user_id)},
                )
            ).mappings())
        except Exception as exc:
            if _is_missing_profile_facts_table(exc):
                return []
            raise
    return [_profile_fact_from_row(row, dek=dek) for row in rows]


async def list_user_memories(user_id: str) -> list[MemoryCandidate]:
    dek = await get_user_dek(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, type, content, content_ciphertext, content_nonce, content_key_id,
                           status, importance, confidence, unsafe,
                           created_at, updated_at, archived_at, expires_at, 0.0 AS similarity
                    FROM memories
                    WHERE user_id = :user_id
                    ORDER BY updated_at DESC
                    LIMIT 50
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings())
    return [_memory_from_row(row, dek=dek) for row in rows]


async def list_safety_events(limit: int = 50) -> list[SafetyEvent]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, message_id, level, reasons, created_at
                    FROM safety_events
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings())
    return [
        SafetyEvent(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            message_id=str(row["message_id"]) if row["message_id"] else None,
            level=SafetyLevel(row["level"]),
            reasons=list(row["reasons"] or []),
            created_at=_aware(row["created_at"]),
        )
        for row in rows
    ]


async def save_subscription_validation(
    user_id: str,
    platform: str,
    entitlement: str,
    valid: bool,
    store_transaction_id: str,
) -> None:
    await ensure_demo_user(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                INSERT INTO subscriptions (
                    id, user_id, platform, entitlement, status, store_transaction_id
                )
                VALUES (
                    :id, :user_id, :platform, :entitlement, :status, :store_transaction_id
                )
                """
            ),
            {
                "id": uuid4(),
                "user_id": _uuid(user_id),
                "platform": platform,
                "entitlement": entitlement,
                "status": "active" if valid else "inactive",
                "store_transaction_id": store_transaction_id,
            },
        )
        await session.commit()


async def create_mood_checkin(user_id: str, label: str, intensity: int | None, note: str | None) -> MoodCheckin:
    await ensure_demo_user(user_id)
    checkin_id = uuid4()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO mood_checkins (id, user_id, label, intensity, note)
                    VALUES (:id, :user_id, :label, :intensity, :note)
                    RETURNING id, user_id, label, intensity, note, created_at
                    """
                ),
                {
                    "id": checkin_id,
                    "user_id": _uuid(user_id),
                    "label": label,
                    "intensity": intensity,
                    "note": note,
                },
            )
        ).mappings().one()
        await session.commit()
    return _mood_checkin_from_row(row)


async def create_reset_session(user_id: str, reset_type: str, notes: str | None = None) -> ResetSession:
    await ensure_demo_user(user_id)
    reset_id = uuid4()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = (
            await session.execute(
                text(
                    """
                    INSERT INTO reset_sessions (id, user_id, reset_type, notes)
                    VALUES (:id, :user_id, :reset_type, :notes)
                    RETURNING id, user_id, reset_type, completed, notes, created_at, completed_at
                    """
                ),
                {"id": reset_id, "user_id": _uuid(user_id), "reset_type": reset_type, "notes": notes},
            )
        ).mappings().one()
        await session.commit()
    return _reset_session_from_row(row)


async def complete_reset_session(reset_id: str, user_id: str) -> ResetSession:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = (
            await session.execute(
                text(
                    """
                    UPDATE reset_sessions
                    SET completed = true, completed_at = COALESCE(completed_at, now())
                    WHERE id = :id AND user_id = :user_id
                    RETURNING id, user_id, reset_type, completed, notes, created_at, completed_at
                    """
                ),
                {"id": _uuid(reset_id), "user_id": _uuid(user_id)},
            )
        ).mappings().one_or_none()
        await session.commit()
    if row is None:
        raise ValueError("reset session not found")
    return _reset_session_from_row(row)


async def get_progress_summary(user_id: str) -> ProgressSummary:
    await ensure_demo_user(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        counts = (
            await session.execute(
                text(
                    """
                    SELECT
                        (SELECT count(*) FROM mood_checkins
                         WHERE user_id = :user_id AND created_at >= now() - interval '7 days') AS checkins_this_week,
                        (SELECT count(*) FROM reset_sessions
                         WHERE user_id = :user_id AND completed = true AND completed_at >= now() - interval '7 days') AS resets_completed_this_week
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings().one()
        checkins = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, label, intensity, note, created_at
                    FROM mood_checkins
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT 8
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings())
        resets = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, reset_type, completed, notes, created_at, completed_at
                    FROM reset_sessions
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT 8
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings())

    themes = _progress_themes_from_checkins([_mood_checkin_from_row(row) for row in checkins])
    return ProgressSummary(
        user_id=user_id,
        checkins_this_week=int(counts["checkins_this_week"] or 0),
        resets_completed_this_week=int(counts["resets_completed_this_week"] or 0),
        themes=themes,
        recent_checkins=[_mood_checkin_from_row(row) for row in checkins],
        recent_resets=[_reset_session_from_row(row) for row in resets],
    )


async def archive_user_memories(user_id: str) -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await session.execute(
            text(
                """
                UPDATE memories
                SET status = 'archived', archived_at = COALESCE(archived_at, now()), updated_at = now()
                WHERE user_id = :user_id AND status = 'active'
                """
            ),
            {"user_id": _uuid(user_id)},
        )
        await session.commit()
    return int(result.rowcount or 0)


async def export_user_data(user_id: str) -> UserDataExport:
    memories = await list_user_memories(user_id)
    profile_facts = await list_user_profile_facts(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        checkins = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, label, intensity, note, created_at
                    FROM mood_checkins
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings())
        resets = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, reset_type, completed, notes, created_at, completed_at
                    FROM reset_sessions
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings())
        messages = list((
            await session.execute(
                text(
                    """
                    SELECT id, session_id, role, content, safety_level, created_at
                    FROM chat_messages
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT 200
                    """
                ),
                {"user_id": _uuid(user_id)},
            )
        ).mappings())
    return UserDataExport(
        user_id=user_id,
        memories=memories,
        profile_facts=profile_facts,
        mood_checkins=[_mood_checkin_from_row(row) for row in checkins],
        reset_sessions=[_reset_session_from_row(row) for row in resets],
        chat_messages=[
            {
                "id": str(row["id"]),
                "session_id": str(row["session_id"]),
                "role": row["role"],
                "content": row["content"],
                "safety_level": row["safety_level"],
                "created_at": _aware(row["created_at"]).isoformat(),
            }
            for row in messages
        ],
    )


async def delete_user_data(user_id: str) -> None:
    parsed_user_id = _uuid(user_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        for table in [
            "reset_sessions",
            "mood_checkins",
            "subscriptions",
            "safety_events",
            "profile_facts",
            "memories",
            "user_encryption_keys",
            "chat_messages",
            "chat_sessions",
        ]:
            try:
                await session.execute(text(f"DELETE FROM {table} WHERE user_id = :user_id"), {"user_id": parsed_user_id})
            except Exception as exc:
                if table == "profile_facts" and _is_missing_profile_facts_table(exc):
                    continue
                raise
        await session.commit()


def _memory_from_row(row, dek: tuple[bytes, str] | None = None) -> MemoryCandidate:
    content = row["content"]
    ciphertext = _row_value(row, "content_ciphertext")
    nonce = _row_value(row, "content_nonce")
    if ciphertext and nonce and dek:
        content = decrypt_text_for_user(str(row["user_id"]), "memories", "content", _bytes(ciphertext), _bytes(nonce), dek[0])
    return MemoryCandidate(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        type=row["type"],
        content=content,
        status=MemoryStatus(row["status"]),
        importance=row["importance"],
        confidence=row["confidence"],
        similarity=row["similarity"] or 0.0,
        unsafe=row["unsafe"],
        created_at=_aware(row["created_at"]),
        updated_at=_aware(row["updated_at"]),
        archived_at=_aware(row["archived_at"]) if row["archived_at"] else None,
        expires_at=_aware(row["expires_at"]) if row["expires_at"] else None,
    )


def _profile_fact_from_row(row, dek: tuple[bytes, str] | None = None) -> ProfileFact:
    value = row["value"]
    ciphertext = _row_value(row, "value_ciphertext")
    nonce = _row_value(row, "value_nonce")
    if ciphertext and nonce and dek:
        value = decrypt_text_for_user(str(row["user_id"]), "profile_facts", "value", _bytes(ciphertext), _bytes(nonce), dek[0])
    return ProfileFact(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        fact_type=row["fact_type"],
        label=row["label"],
        value=value,
        sensitivity=row["sensitivity"],
        source=row["source"],
        confidence=float(row["confidence"]),
        created_at=_aware(row["created_at"]),
        updated_at=_aware(row["updated_at"]),
        expires_at=_aware(row["expires_at"]),
    )


def _mood_checkin_from_row(row) -> MoodCheckin:
    return MoodCheckin(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        label=row["label"],
        intensity=row["intensity"],
        note=row["note"],
        created_at=_aware(row["created_at"]),
    )


def _reset_session_from_row(row) -> ResetSession:
    return ResetSession(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        reset_type=row["reset_type"],
        completed=row["completed"],
        notes=row["notes"],
        created_at=_aware(row["created_at"]),
        completed_at=_aware(row["completed_at"]) if row["completed_at"] else None,
    )


def _progress_themes_from_checkins(checkins: list[MoodCheckin]) -> list[ProgressTheme]:
    if not checkins:
        return []
    theme_counts: dict[str, int] = {}
    for checkin in checkins:
        theme_counts[checkin.label] = theme_counts.get(checkin.label, 0) + 1
    total = max(len(checkins), 1)
    themes = []
    for label, count in sorted(theme_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
        value = min(100, max(20, round((count / total) * 100)))
        tone = "High" if value >= 65 else "Medium" if value >= 40 else "Low"
        themes.append(ProgressTheme(label=label, value=value, tone=tone))
    return themes


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _stable_rule_uuid(rule_id: str) -> UUID:
    return UUID(bytes=rule_id.encode("utf-8").ljust(16, b"\0")[:16])
