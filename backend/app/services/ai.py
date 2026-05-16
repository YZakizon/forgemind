from app.schemas import SafetyLevel


def generate_grounded_response(message: str, mode: str, memory_block: str, guidance_block: str) -> str:
    lowered = message.lower()
    if "angry" in lowered or "rage" in lowered:
        return (
            "That sounds like a lot of heat in your system right now. Before you respond or make a move, "
            "give yourself ten minutes away from the trigger if you can. What is the one thing you need to not do tonight?"
        )
    if "sleep" in lowered or mode == "night_support":
        return (
            "Let’s keep this simple. Your mind is still trying to solve something, but tonight may not be the time to solve it. "
            "Write one line about what can wait until morning, then put the phone down for five minutes."
        )
    if "breakup" in lowered or "ex" in lowered:
        return (
            "That kind of pain can make everything feel urgent. A safer move is to slow the next decision down. "
            "What are you tempted to do right now that you might regret tomorrow?"
        )
    return (
        "That sounds heavy. Let’s slow it down and separate the facts from the pressure around them. "
        "What is taking the most energy right now?"
    )


def validate_response_safety(response: str) -> SafetyLevel:
    unsafe_terms = ("hurt yourself", "hurt someone", "revenge")
    return SafetyLevel.medium if any(term in response.lower() for term in unsafe_terms) else SafetyLevel.low
