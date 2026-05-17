from datetime import UTC, datetime
from math import exp
from app.schemas import MemoryCandidate, MemoryStatus, RankedMemory

TOP_VECTOR_CANDIDATES = 20
PROMPT_MEMORY_MIN = 3
PROMPT_MEMORY_MAX = 5
MIN_CONFIDENCE = 0.35


def recency_score(updated_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(UTC)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    age_days = max((now - updated_at).total_seconds() / 86400, 0)
    return float(exp(-age_days / 30))


def is_prompt_safe(candidate: MemoryCandidate, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if candidate.status != MemoryStatus.active:
        return False
    if candidate.archived_at is not None:
        return False
    if candidate.unsafe:
        return False
    if candidate.confidence < MIN_CONFIDENCE:
        return False
    if candidate.expires_at and candidate.expires_at < now:
        return False
    return True


def rank_memory(candidate: MemoryCandidate, now: datetime | None = None) -> RankedMemory:
    recent = recency_score(candidate.updated_at, now)
    active = 1.0 if candidate.status == MemoryStatus.active else 0.0
    final = (
        candidate.similarity * 0.50
        + candidate.importance * 0.25
        + recent * 0.15
        + active * 0.10
    )
    return RankedMemory(**candidate.model_dump(), recency_score=recent, active_score=active, final_score=final)


def filter_and_rank_memories(
    candidates: list[MemoryCandidate],
    now: datetime | None = None,
    limit: int = PROMPT_MEMORY_MAX,
) -> list[RankedMemory]:
    vector_candidates = candidates[:TOP_VECTOR_CANDIDATES]
    filtered = [candidate for candidate in vector_candidates if is_prompt_safe(candidate, now)]
    ranked = sorted((rank_memory(candidate, now) for candidate in filtered), key=lambda item: item.final_score, reverse=True)
    return ranked[: max(PROMPT_MEMORY_MIN, min(limit, PROMPT_MEMORY_MAX))]


def build_memory_prompt_block(memories: list[RankedMemory]) -> str:
    if not memories:
        return "No relevant memories."
    lines = ["Relevant user memories. Use naturally and only if helpful:"]
    for memory in memories[:PROMPT_MEMORY_MAX]:
        lines.append(f"- {memory.content}")
    return "\n".join(lines)


def extract_memory_candidates(message: str) -> list[str]:
    normalized = message.strip()
    if not normalized:
        return []
    lowered = normalized.lower()
    if any(term in lowered for term in ("kill myself", "suicide", "self-harm", "hurt myself", "weapon")):
        return []
    durable_markers = (
        "every",
        "always",
        "usually",
        "prefer",
        "goal",
        "trying to",
        "work",
        "sleep",
        "relationship",
        "family",
        "father",
        "dad",
        "lonely",
        "burned out",
    )
    if any(marker in normalized.lower() for marker in durable_markers):
        return [normalized[:500]]
    return []
