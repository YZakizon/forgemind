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
        tags=["breakup", "ex", "dumped", "relationship"],
        goal="Help the user tolerate the emotional wave without impulsive contact.",
        do_rules=["Validate the pain without dramatizing it.", "Suggest delaying reactive messages.", "Ask one grounding question."],
        avoid_rules=["Do not encourage stalking, revenge, or pressure."],
        priority=70,
    ),
]


def retrieve_guidance(message: str, rules: list[GuidanceRule] | None = None, limit: int = 3) -> list[GuidanceRule]:
    rules = rules or DEFAULT_GUIDANCE_RULES
    normalized = message.lower()
    scored: list[tuple[int, GuidanceRule]] = []
    for rule in rules:
        if not rule.active:
            continue
        keyword_score = sum(1 for tag in rule.tags if tag.lower() in normalized)
        topic_score = 2 if rule.topic.lower() in normalized else 0
        score = keyword_score + topic_score + rule.priority
        if keyword_score or topic_score:
            scored.append((score, rule))
    return [rule for _, rule in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


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
