from app import main
from app.config import Settings
from app.schemas import SpeechRequest
from app.services.openai_provider import OpenAIProvider


class FakeSpeechResponse:
    content = b"fake-aac"


class FakeSpeech:
    def __init__(self):
        self.request = None

    def create(self, **request):
        self.request = request
        return FakeSpeechResponse()


class FakeTranscript:
    text = "I feel overwhelmed."


class FakeTranscriptions:
    def __init__(self):
        self.request = None

    def create(self, **request):
        self.request = request
        return FakeTranscript()


class FakeAudio:
    def __init__(self):
        self.speech = FakeSpeech()
        self.transcriptions = FakeTranscriptions()


class FakeClient:
    def __init__(self):
        self.audio = FakeAudio()


def test_openai_provider_synthesizes_speech_with_tts_settings():
    settings = Settings(
        tts_provider="openai",
        openai_api_key="test-key",
        openai_tts_model="gpt-4o-mini-tts",
        openai_tts_voice="cedar",
        openai_tts_response_format="aac",
        openai_tts_speed=0.95,
        openai_tts_instructions="Speak calmly.",
    )
    provider = OpenAIProvider(settings)
    fake_client = FakeClient()
    provider.client = fake_client

    audio = provider.synthesize_speech("Take one slow breath.")

    assert audio == b"fake-aac"
    assert fake_client.audio.speech.request == {
        "model": "gpt-4o-mini-tts",
        "voice": "cedar",
        "input": "Take one slow breath.",
        "response_format": "aac",
        "speed": 0.95,
        "extra_body": {"instructions": "Speak calmly."},
    }


def test_speech_endpoint_returns_backend_audio(monkeypatch):
    class FakeProvider:
        tts_enabled = True
        settings = Settings(tts_provider="openai", openai_tts_response_format="aac")

        def synthesize_speech(self, text: str) -> bytes:
            assert text == "I am here."
            return b"audio"

    monkeypatch.setattr(main, "OpenAIProvider", FakeProvider)

    response = main.speech(SpeechRequest(text="I am here."))

    assert response.status_code == 200
    assert response.body == b"audio"
    assert response.media_type == "audio/aac"


def test_speech_endpoint_returns_mpeg_for_deepgram_mp3(monkeypatch):
    class FakeProvider:
        tts_enabled = True
        settings = Settings(tts_provider="deepgram", deepgram_api_key="dg-key", deepgram_tts_encoding="mp3")

        def synthesize_speech(self, text: str) -> bytes:
            assert text == "I am here."
            return b"audio"

    monkeypatch.setattr(main, "OpenAIProvider", FakeProvider)

    response = main.speech(SpeechRequest(text="I am here."))

    assert response.status_code == 200
    assert response.body == b"audio"
    assert response.media_type == "audio/mpeg"


def test_deepgram_provider_synthesizes_speech(monkeypatch):
    captured = {}

    class FakeUrlResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"deepgram-aac"

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["data"] = request.data
        captured["timeout"] = timeout
        return FakeUrlResponse()

    monkeypatch.setattr("app.services.openai_provider.urlopen", fake_urlopen)
    settings = Settings(
        tts_provider="deepgram",
        deepgram_api_key="dg-key",
        deepgram_tts_model="aura-2-thalia-en",
        deepgram_tts_encoding="mp3",
        deepgram_tts_speed=1.05,
    )
    provider = OpenAIProvider(settings)

    audio = provider.synthesize_speech("Stay with this.")

    assert audio == b"deepgram-aac"
    assert "https://api.deepgram.com/v1/speak?" in captured["url"]
    assert "model=aura-2-thalia-en" in captured["url"]
    assert "encoding=mp3" in captured["url"]
    assert "speed=1.05" in captured["url"]
    assert captured["headers"]["Authorization"] == "Token dg-key"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["data"] == b'{"text": "Stay with this."}'


def test_openai_provider_transcribes_audio_with_optional_language_override(tmp_path):
    audio_path = tmp_path / "voice.m4a"
    audio_path.write_bytes(b"fake-audio")
    settings = Settings(openai_api_key="test-key", openai_stt_language="en")
    provider = OpenAIProvider(settings)
    fake_client = FakeClient()
    provider.client = fake_client

    transcript = provider.transcribe_audio(audio_path)

    assert transcript == "I feel overwhelmed."
    assert fake_client.audio.transcriptions.request["language"] == "en"
    assert "natural wording and language" in fake_client.audio.transcriptions.request["prompt"]


def test_openai_provider_transcribes_audio_without_language_for_auto_detect(tmp_path):
    audio_path = tmp_path / "voice.m4a"
    audio_path.write_bytes(b"fake-audio")
    settings = Settings(openai_api_key="test-key", openai_stt_language=None)
    provider = OpenAIProvider(settings)
    fake_client = FakeClient()
    provider.client = fake_client

    provider.transcribe_audio(audio_path)

    assert "language" not in fake_client.audio.transcriptions.request
