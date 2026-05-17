import re

from app.schemas import GuidanceRule, SafetyLevel


DEFAULT_GUIDANCE_RULES = [
    GuidanceRule(
        id="burnout-basic",
        topic="burnout",
        tags=["burnout", "work", "exhausted", "tired"],
        goal="Help the user lower pressure and identify the next controllable step.",
        do_rules=["Name the load plainly.", "Separate urgent from important.", "Suggest one small recovery action."],
        avoid_rules=["Do not glamorize overwork.", "Do not prescribe medical treatment."],
        priority=80,
    ),
    GuidanceRule(
        id="anger-reset",
        topic="anger",
        tags=["anger", "angry", "rage", "furious"],
        goal="Help the user pause before acting and reduce immediate escalation.",
        do_rules=["Slow the pace.", "Encourage space from the trigger.", "Focus on what is safe to do next."],
        avoid_rules=["Do not validate revenge.", "Do not encourage confrontation while escalated."],
        safety_level=SafetyLevel.medium,
        priority=90,
    ),
    GuidanceRule(
        id="sleep-support",
        topic="sleep",
        tags=["sleep", "insomnia", "night", "can't sleep"],
        goal="Help the user quiet rumination and prepare for rest.",
        do_rules=["Keep the response brief.", "Suggest a low-effort wind-down step.", "Avoid complex planning at night."],
        avoid_rules=["Do not shame the user for being awake.", "Do not make medical claims."],
        priority=60,
    ),
    GuidanceRule(
        id="breakup-support",
        topic="breakup",
        tags=["breakup", "ex", "dumped", "relationship", "heartbreak"],
        goal="Help the user tolerate the emotional wave without impulsive contact.",
        do_rules=["Validate the pain without dramatizing it.", "Suggest delaying reactive messages.", "Ask one grounding question."],
        avoid_rules=["Do not encourage stalking, revenge, or pressure."],
        priority=70,
    ),
    GuidanceRule(
        id="anxiety-grounding",
        topic="anxiety",
        tags=["anxiety", "anxious", "overthinking", "spiral", "worried"],
        goal="Help the user slow the spiral and name the next concrete action.",
        do_rules=["Use steady pacing.", "Separate facts from feared outcomes.", "Offer one grounding step."],
        avoid_rules=["Do not argue with the fear at length.", "Do not promise certainty."],
        priority=75,
    ),
    GuidanceRule(
        id="divorce-support",
        topic="divorce",
        tags=["divorce", "separation", "custody", "co-parent", "lawyer"],
        goal="Help the user stay grounded during practical and emotional divorce pressure.",
        do_rules=["Acknowledge the stakes.", "Encourage one practical next step.", "Keep advice emotionally steady."],
        avoid_rules=["Do not give legal advice.", "Do not escalate conflict with the former partner."],
        priority=72,
    ),
    GuidanceRule(
        id="dating-stress",
        topic="dating",
        tags=["dating", "date", "rejected", "ghosted", "text back"],
        goal="Help the user respond from self-respect instead of panic or performance pressure.",
        do_rules=["Normalize uncertainty.", "Encourage a direct but low-pressure action.", "Protect the user's dignity."],
        avoid_rules=["Do not encourage games, pressure, or manipulation."],
        priority=66,
    ),
    GuidanceRule(
        id="wedding-pressure",
        topic="wedding stress",
        tags=["wedding", "fiance", "fiancee", "engagement", "married"],
        goal="Help the user separate relationship care from event pressure.",
        do_rules=["Name competing pressures.", "Suggest one calm conversation or boundary.", "Keep focus on values."],
        avoid_rules=["Do not frame normal nerves as a diagnosis.", "Do not push a major decision from one message."],
        priority=68,
    ),
    GuidanceRule(
        id="loneliness-support",
        topic="loneliness",
        tags=["lonely", "alone", "isolated", "no one", "disconnected"],
        goal="Help the user feel less alone while identifying one safe connection step.",
        do_rules=["Reflect the isolation plainly.", "Suggest a small reachable contact.", "Avoid pressure or shame."],
        avoid_rules=["Do not create dependency on Forge.", "Do not imply the app replaces people."],
        priority=74,
    ),
    GuidanceRule(
        id="fatherhood-pressure",
        topic="fatherhood",
        tags=["father", "dad", "kid", "children", "parent"],
        goal="Help the user handle provider, patience, and family pressure without self-attack.",
        do_rules=["Respect the responsibility.", "Focus on repair and the next calm action.", "Use practical language."],
        avoid_rules=["Do not shame the user.", "Do not minimize family stress."],
        priority=64,
    ),
    GuidanceRule(
        id="family-conflict",
        topic="family conflict",
        tags=["family", "parents", "brother", "sister", "argument", "conflict"],
        goal="Help the user lower reactivity and choose a boundary or repair step.",
        do_rules=["Name the relational pressure.", "Suggest space before hard conversations.", "Offer one boundary phrase."],
        avoid_rules=["Do not encourage cutoff as the first move.", "Do not assign blame without context."],
        priority=62,
    ),
]


def retrieve_guidance(message: str, rules: list[GuidanceRule] | None = None, limit: int = 3) -> list[GuidanceRule]:
    rules = rules or DEFAULT_GUIDANCE_RULES
    normalized = message.lower()
    scored: list[tuple[int, GuidanceRule]] = []
    for rule in rules:
        if not rule.active:
            continue
        keyword_score = sum(1 for tag in rule.tags if _matches_phrase(normalized, tag))
        topic_score = 2 if _matches_phrase(normalized, rule.topic) else 0
        score = keyword_score + topic_score + rule.priority
        if keyword_score or topic_score:
            scored.append((score, rule))
    return [rule for _, rule in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def _matches_phrase(normalized_message: str, phrase: str) -> bool:
    normalized_phrase = phrase.lower().strip()
    if len(normalized_phrase) <= 3:
        return re.search(rf"\b{re.escape(normalized_phrase)}\b", normalized_message) is not None
    return normalized_phrase in normalized_message


def build_guidance_prompt_block(rules: list[GuidanceRule]) -> str:
    if not rules:
        return "No specific guidance rules matched."
    lines = ["Approved guidance to apply compactly:"]
    for rule in rules:
        lines.append(f"- {rule.topic}: {rule.goal}")
        if rule.do_rules:
            lines.append(f"  Do: {'; '.join(rule.do_rules)}")
        if rule.avoid_rules:
            lines.append(f"  Avoid: {'; '.join(rule.avoid_rules)}")
    return "\n".join(lines)
