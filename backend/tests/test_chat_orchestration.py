from app.main import chat
from app.schemas import ChatRequest, SafetyLevel


def test_chat_returns_crisis_response_without_normal_coaching():
    response = chat(ChatRequest(user_id="user-1", message="I want to kill myself"))
    assert response.safety_level == SafetyLevel.crisis
    assert "emergency services" in response.response


def test_chat_uses_guidance_for_anger():
    response = chat(ChatRequest(user_id="user-1", message="I am angry and want to text him now"))
    assert response.safety_level in {SafetyLevel.low, SafetyLevel.medium}
    assert "anger" in response.guidance_topics


def test_chat_stops_normal_coaching_for_high_risk():
    response = chat(ChatRequest(user_id="user-1", message="I am not safe and there is a weapon here"))
    assert response.safety_level == SafetyLevel.high
    assert response.guidance_topics == []
    assert "emergency services" in response.response
