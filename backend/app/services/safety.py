from app.schemas import SafetyLevel, SafetyResult


CRISIS_RESPONSE = (
    "I’m really glad you said something. If you might hurt yourself or someone else, "
    "call emergency services now or go to the nearest ER. If you are in the U.S. or Canada, "
    "call or text 988 for immediate crisis support. If you can, move away from anything you "
    "could use to hurt yourself and contact one trusted person nearby right now."
)

CRISIS_TERMS = {
    "kill myself",
    "suicide",
    "end my life",
    "want to die",
    "hurt myself",
    "self harm",
    "self-harm",
    "overdose",
}

HIGH_RISK_TERMS = {
    "hurt someone",
    "kill him",
    "kill her",
    "abuse",
    "he hit me",
    "she hit me",
    "not safe",
    "weapon",
}

MEDIUM_RISK_TERMS = {
    "hopeless",
    "panic",
    "can't cope",
    "cannot cope",
    "rage",
    "out of control",
    "breakdown",
}


def classify_safety(message: str) -> SafetyResult:
    normalized = message.lower()
    reasons: list[str] = []

    for term in CRISIS_TERMS:
        if term in normalized:
            reasons.append(term)
    if reasons:
        return SafetyResult(level=SafetyLevel.crisis, reasons=reasons, crisis_response=CRISIS_RESPONSE)

    for term in HIGH_RISK_TERMS:
        if term in normalized:
            reasons.append(term)
    if reasons:
        return SafetyResult(level=SafetyLevel.high, reasons=reasons)

    for term in MEDIUM_RISK_TERMS:
        if term in normalized:
            reasons.append(term)
    if reasons:
        return SafetyResult(level=SafetyLevel.medium, reasons=reasons)

    return SafetyResult(level=SafetyLevel.low)
