from app.schemas import SafetyLevel


def generate_grounded_response(message: str, mode: str, memory_block: str, guidance_block: str) -> str:
    lowered = message.lower()
    if "angry" in lowered or "rage" in lowered:
        return (
            "There is a lot of heat in your system right now. Before you respond or make a move, "
            "give yourself ten minutes away from the trigger if you can. What is the one thing you need to not do tonight?"
        )
    if "sleep" in lowered or mode == "night_support":
        return (
            "Let’s keep this simple. Your mind is still trying to solve something, but tonight may not be the time to solve it. "
            "Write one line about what can wait until morning, then put the phone down for five minutes."
        )
    if "breakup" in lowered or "ex" in lowered:
        return (
            "Breakup pain can make everything feel urgent. A safer move is to slow the next decision down. "
            "What are you tempted to do right now that you might regret tomorrow?"
        )
    return (
        "Let’s slow this down and separate the facts from the pressure around them. "
        "What is taking the most energy right now?"
    )


def validate_response_safety(response: str) -> SafetyLevel:
    unsafe_terms = ("hurt yourself", "hurt someone", "revenge")
    return SafetyLevel.medium if any(term in response.lower() for term in unsafe_terms) else SafetyLevel.low


def generate_fallback_reply_suggestions(user_message: str, forge_message: str, mode: str) -> list[str]:
    context = f"{user_message} {forge_message} {mode}".lower()
    if any(term in context for term in ["angry", "rage", "react", "disrespect"]):
        return ["I need to cool down", "I want to respond", "I feel disrespected"]
    if any(term in context for term in ["breakup", "ex", "partner", "relationship", "dating"]):
        return ["I keep replaying it", "I need clarity", "I do not want to chase"]
    if any(term in context for term in ["sleep", "tired", "night", "exhausted"]):
        return ["My mind will not stop", "I need to wind down", "Tomorrow can wait"]
    if any(term in context for term in ["work", "job", "boss", "deadline", "burnout", "overloaded"]):
        return ["I feel overloaded", "The deadline is urgent", "Help me prioritize"]
    return ["The pressure", "I feel stuck", "Help me name it"]
