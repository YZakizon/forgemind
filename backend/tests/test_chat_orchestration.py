import asyncio

from app.main import VoiceTranscriptSegment, chat, merge_transcript_segments, reply_suggestions, split_response_parts, split_tts_chunks
from app.schemas import ChatRequest, ReplySuggestionsRequest, SafetyLevel
from app.services.ai import generate_grounded_response
from app.services.openai_provider import build_history_block, parse_reply_suggestions


def test_chat_returns_crisis_response_without_normal_coaching():
    response = asyncio.run(chat(ChatRequest(user_id="user-1", message="I want to kill myself")))
    assert response.safety_level == SafetyLevel.crisis
    assert "emergency services" in response.response


def test_chat_uses_guidance_for_anger():
    response = asyncio.run(chat(ChatRequest(user_id="user-1", message="I am angry and want to text him now")))
    assert response.safety_level in {SafetyLevel.low, SafetyLevel.medium}
    assert "anger" in response.guidance_topics


def test_chat_stops_normal_coaching_for_high_risk():
    response = asyncio.run(chat(ChatRequest(user_id="user-1", message="I am not safe and there is a weapon here")))
    assert response.safety_level == SafetyLevel.high
    assert response.guidance_topics == []
    assert "emergency services" in response.response


def test_fallback_response_avoids_repetitive_sounds_like_opening():
    response = generate_grounded_response(
        "I am overwhelmed with everything",
        "think_clearly",
        "",
        "",
    )
    assert not response.lower().startswith(("it sounds like", "that sounds like"))


def test_history_block_formats_recent_conversation_context():
    block = build_history_block(
        [
            {"role": "user", "text": "This is the first thing I said."},
            {"role": "forge", "text": "What is taking the most energy?"},
            {"role": "user", "text": "Work pressure and not sleeping."},
        ]
    )

    assert "User: This is the first thing I said." in block
    assert "Forge: What is taking the most energy?" in block
    assert "User: Work pressure and not sleeping." in block


def test_reply_suggestions_fallback_answers_latest_forge_question():
    response = asyncio.run(
        reply_suggestions(
            ReplySuggestionsRequest(
                user_id="user-1",
                user_message="I am overloaded with work",
                forge_message="What is taking the most energy right now?",
                mode="vent",
                history=[],
            )
        )
    )

    assert response.suggestions == ["I feel overloaded", "The deadline is urgent", "Help me prioritize"]


def test_parse_reply_suggestions_rejects_questions_and_duplicates():
    suggestions = parse_reply_suggestions(
        '{"suggestions":["The deadline","The deadline","What should I do?","I need boundaries"]}'
    )

    assert suggestions == ["The deadline", "I need boundaries"]


def test_split_response_parts_separates_body_and_question():
    parts = split_response_parts("Yeah, that is a lot. Take one breath first. What feels most urgent?")

    assert parts.body == "Yeah, that is a lot. Take one breath first."
    assert parts.question == "What feels most urgent?"


def test_split_response_parts_does_not_put_leading_question_in_body():
    parts = split_response_parts("What would help most? Start by naming the pressure. What feels urgent?")

    assert parts.body == "Start by naming the pressure."
    assert parts.question == "What feels urgent?"


def test_merge_transcript_segments_deduplicates_overlapping_text():
    transcript = merge_transcript_segments(
        [
            VoiceTranscriptSegment(index=0, text="I feel pressure from work and I cannot sleep", started_at_ms=0, ended_at_ms=5200),
            VoiceTranscriptSegment(index=1, text="and I cannot sleep because my mind keeps going", started_at_ms=4700, ended_at_ms=9400),
        ]
    )

    assert transcript == "I feel pressure from work and I cannot sleep because my mind keeps going"


def test_merge_transcript_segments_orders_by_index_and_cleans_punctuation_spacing():
    transcript = merge_transcript_segments(
        [
            VoiceTranscriptSegment(index=1, text="I need one next step .", started_at_ms=3000, ended_at_ms=6200),
            VoiceTranscriptSegment(index=0, text="today feels heavy", started_at_ms=0, ended_at_ms=2800),
        ]
    )

    assert transcript == "Today feels heavy I need one next step."


def test_merge_transcript_segments_drops_prompt_echo_from_silent_pause():
    transcript = merge_transcript_segments(
        [
            VoiceTranscriptSegment(index=0, text="I feel stuck at work", started_at_ms=0, ended_at_ms=3200),
            VoiceTranscriptSegment(index=1, text="Preserve the users natural wording.", started_at_ms=3600, ended_at_ms=5200),
            VoiceTranscriptSegment(index=2, text="and I cannot switch off", started_at_ms=6500, ended_at_ms=9000),
        ]
    )

    assert transcript == "I feel stuck at work and I cannot switch off"


def test_split_tts_chunks_keeps_body_chunks_small_and_ordered():
    chunks = split_tts_chunks(
        "Start with one breath. Name the pressure without solving it yet. "
        "Then pick one concrete thing you can put down for the next hour.",
        max_chars=70,
    )

    assert chunks == [
        "Start with one breath. Name the pressure without solving it yet.",
        "Then pick one concrete thing you can put down for the next hour.",
    ]
