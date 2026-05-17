from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import text

from app.db import get_sessionmaker
from app.schemas import GuidanceRule, MemoryCandidate, MemoryStatus, SafetyEvent, SafetyLevel
from app.services.guidance import DEFAULT_GUIDANCE_RULES


def _uuid(value: str) -> UUID:
    return UUID(value)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


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
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, type, content, status, importance, confidence, unsafe,
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
    return [_memory_from_row(row) for row in rows]


async def insert_memories(user_id: str, contents: list[str], embedding_by_content: dict[str, list[float]]) -> None:
    if not contents:
        return
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        for content in contents:
            await session.execute(
                text(
                    """
                    INSERT INTO memories (
                        id, user_id, type, content, status, importance, confidence, unsafe, embedding
                    )
                    VALUES (
                        :id, :user_id, 'emotional_pattern', :content, 'active', 0.55, 0.65, false,
                        CAST(:embedding AS vector)
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "user_id": _uuid(user_id),
                    "content": content,
                    "embedding": _vector_literal(embedding_by_content[content]),
                },
            )
        await session.commit()


async def list_user_memories(user_id: str) -> list[MemoryCandidate]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        rows = list((
            await session.execute(
                text(
                    """
                    SELECT id, user_id, type, content, status, importance, confidence, unsafe,
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
    return [_memory_from_row(row) for row in rows]


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


def _memory_from_row(row) -> MemoryCandidate:
    return MemoryCandidate(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        type=row["type"],
        content=row["content"],
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


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _stable_rule_uuid(rule_id: str) -> UUID:
    return UUID(bytes=rule_id.encode("utf-8").ljust(16, b"\0")[:16])
