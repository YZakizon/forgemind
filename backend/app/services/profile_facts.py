from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


DEFAULT_PROFILE_FACT_TTL_DAYS = 180
DATE_PROFILE_FACT_TTL_DAYS = 365
MAX_PROFILE_FACT_VALUE_LENGTH = 160
ALLOWED_FACT_TYPES = {"name", "relationship", "workplace", "location", "date", "belief", "health_context", "habit", "timezone"}
ALLOWED_SENSITIVITIES = {"normal", "personal", "health"}


@dataclass(frozen=True)
class ExtractedProfileFact:
    fact_type: str
    label: str
    value: str
    expires_at: datetime
    sensitivity: str = "normal"
    confidence: float = 0.65
    source: str = "chat"


def _clean_value(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip(" .,!?:;\"'")).strip()
    return cleaned[:MAX_PROFILE_FACT_VALUE_LENGTH]


def _expires_at(days: int, now: datetime | None = None) -> datetime:
    base = now or datetime.now(UTC)
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    return base + timedelta(days=days)


def _append_fact(
    facts: list[ExtractedProfileFact],
    fact_type: str,
    label: str,
    value: str,
    ttl_days: int = DEFAULT_PROFILE_FACT_TTL_DAYS,
    confidence: float = 0.65,
    sensitivity: str = "normal",
    source: str = "chat",
    now: datetime | None = None,
) -> None:
    cleaned = _clean_value(value)
    if len(cleaned) < 2:
        return
    facts.append(
        ExtractedProfileFact(
            fact_type=fact_type,
            label=label,
            value=cleaned,
            expires_at=_expires_at(ttl_days, now),
            sensitivity=sensitivity if sensitivity in ALLOWED_SENSITIVITIES else "normal",
            confidence=confidence,
            source=source,
        )
    )


def build_profile_facts_prompt_block(facts: list[Any]) -> str:
    active_facts = [fact for fact in facts if getattr(fact, "expires_at", datetime.now(UTC)) > datetime.now(UTC)]
    lines = ["Personal facts. Use only if directly helpful; do not repeat private facts unnecessarily."]
    if not any(getattr(fact, "fact_type", "") == "timezone" for fact in active_facts):
        lines.append("- Timezone is unknown. If timing matters, ask the user their timezone in a low-pressure way.")
    for fact in active_facts[:12]:
        sensitivity = getattr(fact, "sensitivity", "normal")
        type_label = f"{getattr(fact, 'fact_type', 'fact')}:{getattr(fact, 'label', 'value')}"
        value = getattr(fact, "value", "")
        if sensitivity == "health":
            lines.append(f"- {type_label}: user mentioned {value}. Do not diagnose or make medical claims.")
        else:
            lines.append(f"- {type_label}: {value}")
    lines.append("You may ask about habits only when relevant, non-intrusive, and non-private.")
    return "\n".join(lines)


def extract_profile_facts(message: str, now: datetime | None = None) -> list[ExtractedProfileFact]:
    text = message.strip()
    if not text:
        return []

    facts: list[ExtractedProfileFact] = []
    patterns = [
        ("workplace", "workplace", r"\b(?:i work at|i work for|my workplace is|my company is)\s+([A-Z][\w&.\- ]{1,80})"),
        ("location", "city", r"\b(?:i live in|my city is|i moved to)\s+([A-Z][A-Za-z .'-]{1,80})"),
        ("location", "country", r"\b(?:my country is|i am from|i'm from)\s+([A-Z][A-Za-z .'-]{1,80})"),
        ("timezone", "timezone", r"\b(?:my timezone is|i am in timezone|i'm in timezone)\s+([A-Za-z_/\-+0-9: ]{2,80})"),
        ("date", "birthday", r"\b(?:my birthday is|i was born on|i was born)\s+([A-Za-z0-9, /\-]{3,40})"),
        ("date", "graduation", r"\b(?:my graduation date is|i graduated on|i graduate on)\s+([A-Za-z0-9, /\-]{3,40})"),
        ("belief", "belief", r"\b(?:i believe that|i believe|my belief is)\s+([^.!?\n]{3,160})"),
        ("habit", "exercise", r"\b(?:i go to the gym|i go to gym|i workout|i work out|i bike|i'm biking|i run)\s+([^.!?\n]{3,120})"),
        ("health_context", "recurring_symptom", r"\b(?:i keep|i usually|i always|every morning i|every night i)\s+([^.!?\n]*(?:sneez|cough|headache|pain|tired|tiredness|dizzy|nauseous|congested)[^.!?\n]*)"),
    ]
    for fact_type, label, pattern in patterns:
        ttl = DATE_PROFILE_FACT_TTL_DAYS if fact_type in {"date", "timezone"} else DEFAULT_PROFILE_FACT_TTL_DAYS
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            sensitivity = "health" if fact_type == "health_context" else "normal"
            _append_fact(facts, fact_type, label, match.group(1), ttl_days=ttl, sensitivity=sensitivity, now=now)

    relationship_pattern = re.compile(
        r"\bmy\s+(wife|husband|girlfriend|boyfriend|fiancee|fiancé|fiance|partner|ex|mother|father|dad|mom|brother|sister|friend|manager|boss)\s+(?:is\s+)?([A-Z][A-Za-z .'-]{1,60})",
        flags=re.IGNORECASE,
    )
    for match in relationship_pattern.finditer(text):
        relationship = _clean_value(match.group(1)).lower()
        name = _clean_value(match.group(2))
        _append_fact(facts, "relationship", relationship, name, now=now)

    deduped: dict[tuple[str, str, str], ExtractedProfileFact] = {}
    for fact in facts:
        key = (fact.fact_type.lower(), fact.label.lower(), fact.value.lower())
        deduped[key] = fact
    return list(deduped.values())


def profile_facts_from_ai_payload(items: Any, now: datetime | None = None) -> list[ExtractedProfileFact]:
    if not isinstance(items, list):
        return []
    facts: list[ExtractedProfileFact] = []
    for item in items[:8]:
        if not isinstance(item, dict):
            continue
        fact_type = str(item.get("fact_type", "")).strip()
        label = str(item.get("label", "")).strip()
        value = str(item.get("value", "")).strip()
        sensitivity = str(item.get("sensitivity", "normal")).strip()
        if fact_type not in ALLOWED_FACT_TYPES or not label or not value:
            continue
        ttl_days = int(item.get("ttl_days", 90 if sensitivity == "health" else DEFAULT_PROFILE_FACT_TTL_DAYS))
        ttl_days = max(7, min(ttl_days, 365))
        confidence = float(item.get("confidence", 0.65))
        _append_fact(
            facts,
            fact_type,
            label,
            value,
            ttl_days=ttl_days,
            confidence=max(0.0, min(confidence, 1.0)),
            sensitivity=sensitivity,
            source="ai",
            now=now,
        )
    return facts
