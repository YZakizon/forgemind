from app.schemas import SafetyLevel
from app.services.safety import classify_safety


def test_crisis_language_overrides_normal_chat():
    result = classify_safety("I want to die tonight")
    assert result.level == SafetyLevel.crisis
    assert result.crisis_response is not None
    assert "988" in result.crisis_response


def test_high_risk_language_is_detected():
    result = classify_safety("I am not safe and there is a weapon here")
    assert result.level == SafetyLevel.high


def test_low_risk_message_is_low():
    result = classify_safety("I am stressed about work")
    assert result.level == SafetyLevel.low
