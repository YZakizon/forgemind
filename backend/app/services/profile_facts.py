from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


DEFAULT_PROFILE_FACT_TTL_DAYS = 180
DATE_PROFILE_FACT_TTL_DAYS = 365
HEALTH_PROFILE_FACT_TTL_DAYS = 90
MAX_PROFILE_FACT_VALUE_LENGTH = 160
ALLOWED_FACT_TYPES = {"name", "relationship", "workplace", "location", "date", "belief", "health_context", "habit", "timezone"}
ALLOWED_SENSITIVITIES = {"normal", "personal", "health"}

DEFAULT_CAPTURE_TERMS: dict[str, list[str]] = {
    "name": ["my name is", "call me"],
    "relationship": ["wife", "husband", "girlfriend", "boyfriend", "partner", "manager", "boss"],
    "workplace": ["work at", "work for", "company", "workplace"],
    "location": ["live in", "city", "country", "moved to"],
    "date": ["birthday", "graduation"],
    "belief": ["i believe"],
    "health_context": ["sneezing", "cough", "headache", "pain", "dizzy", "nauseous", "congested"],
    "habit": ["gym", "workout", "biking", "bike", "running", "run"],
    "timezone": ["timezone"],
}
DEFAULT_BLOCKED_TERMS: dict[str, list[str]] = {
    "all": [
        "credit card",
        "debit card",
        "password",
        "social security",
        "ssn",
        "passport",
        "driver license",
        "bank account",
        "routing number",
    ]
}
DEFAULT_TTL_DAYS_BY_TYPE: dict[str, int] = {
    "name": DEFAULT_PROFILE_FACT_TTL_DAYS,
    "relationship": DEFAULT_PROFILE_FACT_TTL_DAYS,
    "workplace": DEFAULT_PROFILE_FACT_TTL_DAYS,
    "location": DEFAULT_PROFILE_FACT_TTL_DAYS,
    "date": DATE_PROFILE_FACT_TTL_DAYS,
    "belief": DEFAULT_PROFILE_FACT_TTL_DAYS,
    "health_context": HEALTH_PROFILE_FACT_TTL_DAYS,
    "habit": DEFAULT_PROFILE_FACT_TTL_DAYS,
    "timezone": DATE_PROFILE_FACT_TTL_DAYS,
}


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


def default_profile_fact_policy() -> dict[str, dict[str, list[str]] | dict[str, int]]:
    return {
        "capture_terms": {key: list(values) for key, values in DEFAULT_CAPTURE_TERMS.items()},
        "blocked_terms": {key: list(values) for key, values in DEFAULT_BLOCKED_TERMS.items()},
        "ttl_days_by_type": dict(DEFAULT_TTL_DAYS_BY_TYPE),
    }


def normalize_profile_fact_policy(policy: Any | None) -> dict[str, dict[str, list[str]] | dict[str, int]]:
    default = default_profile_fact_policy()
    if policy is None:
        return default
    raw = policy.model_dump() if hasattr(policy, "model_dump") else dict(policy)
    capture_terms = _normalize_terms(raw.get("capture_terms"), default["capture_terms"])
    blocked_terms = _normalize_terms(raw.get("blocked_terms"), default["blocked_terms"], allow_all=True)
    ttl_days_by_type = _normalize_ttls(raw.get("ttl_days_by_type"), default["ttl_days_by_type"])
    return {"capture_terms": capture_terms, "blocked_terms": blocked_terms, "ttl_days_by_type": ttl_days_by_type}


def _normalize_terms(value: Any, default: dict[str, list[str]], allow_all: bool = False) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}
    allowed_keys = set(ALLOWED_FACT_TYPES)
    if allow_all:
        allowed_keys.add("all")
    source = value if isinstance(value, dict) else {}
    for key in allowed_keys:
        raw_terms = source.get(key, default.get(key, []))
        if not isinstance(raw_terms, list):
            raw_terms = []
        terms = []
        seen = set()
        for item in raw_terms[:80]:
            term = _clean_value(str(item)).lower()
            if len(term) < 2 or term in seen:
                continue
            seen.add(term)
            terms.append(term)
        if terms or key in default:
            normalized[key] = terms
    return normalized


def _normalize_ttls(value: Any, default: dict[str, int]) -> dict[str, int]:
    source = value if isinstance(value, dict) else {}
    normalized: dict[str, int] = {}
    for fact_type in ALLOWED_FACT_TYPES:
        try:
            ttl = int(source.get(fact_type, default.get(fact_type, DEFAULT_PROFILE_FACT_TTL_DAYS)))
        except (TypeError, ValueError):
            ttl = default.get(fact_type, DEFAULT_PROFILE_FACT_TTL_DAYS)
        normalized[fact_type] = max(30, min(ttl, 365))
    return normalized


def _ttl_for_type(fact_type: str, policy: dict[str, Any] | None = None) -> int:
    if policy:
        ttl = policy.get("ttl_days_by_type", {}).get(fact_type)
        if isinstance(ttl, int):
            return ttl
    return DEFAULT_TTL_DAYS_BY_TYPE.get(fact_type, DEFAULT_PROFILE_FACT_TTL_DAYS)


def _is_blocked(text: str, fact_type: str, policy: dict[str, Any]) -> bool:
    haystack = text.lower()
    blocked_terms = policy.get("blocked_terms", {})
    terms = list(blocked_terms.get("all", [])) + list(blocked_terms.get(fact_type, []))
    return any(term and term in haystack for term in terms)


def _sentence_for_term(text: str, term: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if term.lower() in sentence.lower():
            return sentence
    return text


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


def extract_profile_facts(message: str, now: datetime | None = None, policy: Any | None = None) -> list[ExtractedProfileFact]:
    text = message.strip()
    if not text:
        return []

    normalized_policy = normalize_profile_fact_policy(policy)
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
        ttl = _ttl_for_type(fact_type, normalized_policy)
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if _is_blocked(match.group(0), fact_type, normalized_policy):
                continue
            sensitivity = "health" if fact_type == "health_context" else "normal"
            _append_fact(facts, fact_type, label, match.group(1), ttl_days=ttl, sensitivity=sensitivity, now=now)

    relationship_pattern = re.compile(
        r"\bmy\s+(wife|husband|girlfriend|boyfriend|fiancee|fiancé|fiance|partner|ex|mother|father|dad|mom|brother|sister|friend|manager|boss)\s+(?:is\s+)?([A-Z][A-Za-z .'-]{1,60})",
        flags=re.IGNORECASE,
    )
    for match in relationship_pattern.finditer(text):
        if _is_blocked(match.group(0), "relationship", normalized_policy):
            continue
        relationship = _clean_value(match.group(1)).lower()
        name = _clean_value(match.group(2))
        _append_fact(facts, "relationship", relationship, name, ttl_days=_ttl_for_type("relationship", normalized_policy), now=now)

    capture_terms = normalized_policy.get("capture_terms", {})
    for fact_type, terms in capture_terms.items():
        if fact_type not in ALLOWED_FACT_TYPES:
            continue
        for term in terms:
            if not term or term not in text.lower():
                continue
            sentence = _sentence_for_term(text, term)
            if _is_blocked(sentence, fact_type, normalized_policy):
                continue
            sensitivity = "health" if fact_type == "health_context" else "normal"
            _append_fact(
                facts,
                fact_type,
                term,
                sentence,
                ttl_days=_ttl_for_type(fact_type, normalized_policy),
                confidence=0.55,
                sensitivity=sensitivity,
                source="policy",
                now=now,
            )

    deduped: dict[tuple[str, str, str], ExtractedProfileFact] = {}
    for fact in facts:
        key = (fact.fact_type.lower(), fact.label.lower(), fact.value.lower())
        deduped[key] = fact
    return list(deduped.values())


def profile_facts_from_ai_payload(items: Any, now: datetime | None = None, policy: Any | None = None) -> list[ExtractedProfileFact]:
    if not isinstance(items, list):
        return []
    normalized_policy = normalize_profile_fact_policy(policy)
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
        if _is_blocked(f"{label} {value}", fact_type, normalized_policy):
            continue
        ttl_days = int(item.get("ttl_days", _ttl_for_type(fact_type, normalized_policy)))
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
