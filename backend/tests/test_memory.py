from datetime import UTC, datetime, timedelta

from app.schemas import MemoryCandidate, MemoryStatus
from app.services.memory import extract_memory_candidates, filter_and_rank_memories, recency_score
from app.services.profile_facts import build_profile_facts_prompt_block, extract_profile_facts, profile_facts_from_ai_payload


def candidate(identifier: str, **overrides) -> MemoryCandidate:
    now = datetime.now(UTC)
    data = {
        "id": identifier,
        "user_id": "user-1",
        "type": "emotional_pattern",
        "content": f"Memory {identifier}",
        "status": MemoryStatus.active,
        "importance": 0.5,
        "confidence": 0.8,
        "similarity": 0.5,
        "unsafe": False,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return MemoryCandidate(**data)


def test_recency_score_decays_with_age():
    now = datetime.now(UTC)
    recent = recency_score(now - timedelta(days=1), now)
    old = recency_score(now - timedelta(days=90), now)
    assert recent > old


def test_filter_and_rank_excludes_archived_unsafe_and_low_confidence():
    ranked = filter_and_rank_memories(
        [
            candidate("good", similarity=0.9),
            candidate("archived", status=MemoryStatus.archived),
            candidate("unsafe", unsafe=True),
            candidate("low-confidence", confidence=0.1),
        ],
        now=datetime.now(UTC),
        limit=5,
    )
    assert [item.id for item in ranked] == ["good"]


def test_ranking_uses_similarity_importance_recency_and_active_status():
    now = datetime.now(UTC)
    ranked = filter_and_rank_memories(
        [
            candidate("older", similarity=0.7, importance=0.5, updated_at=now - timedelta(days=90)),
            candidate("important", similarity=0.7, importance=0.9, updated_at=now),
        ],
        now=now,
        limit=5,
    )
    assert ranked[0].id == "important"
    assert ranked[0].final_score > ranked[1].final_score


def test_memory_extraction_skips_safety_content():
    assert extract_memory_candidates("I always feel like I want to kill myself") == []


def test_memory_extraction_keeps_durable_context():
    assert extract_memory_candidates("I usually sleep badly before family conflict")


def test_profile_fact_extraction_captures_habits_health_and_timezone():
    facts = extract_profile_facts("My timezone is America/Los_Angeles. I go to gym every Monday. I keep sneezing every morning.")
    keys = {(fact.fact_type, fact.label) for fact in facts}

    assert ("timezone", "timezone") in keys
    assert ("habit", "exercise") in keys
    assert ("health_context", "recurring_symptom") in keys
    assert [fact for fact in facts if fact.fact_type == "health_context"][0].sensitivity == "health"


def test_profile_fact_ai_payload_is_validated():
    facts = profile_facts_from_ai_payload(
        [
            {
                "fact_type": "habit",
                "label": "exercise",
                "value": "bikes every weekend",
                "sensitivity": "normal",
                "ttl_days": 180,
                "confidence": 0.8,
            },
            {"fact_type": "secret", "label": "password", "value": "abc123"},
        ]
    )

    assert len(facts) == 1
    assert facts[0].fact_type == "habit"


def test_profile_fact_prompt_asks_for_timezone_when_missing():
    block = build_profile_facts_prompt_block([])

    assert "Timezone is unknown" in block
    assert "non-intrusive" in block
