from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openai import OpenAI

from app.config import Settings, get_settings
from app.services.ai import generate_grounded_response

CONVERSATION_INSTRUCTIONS = """You are ForgeMind, an AI mental health support companion for men.
You are not a therapist, doctor, emergency service, or diagnostic tool.
Tone: calm, direct, practical, private, grounded, emotionally safe, masculine-neutral, and non-clinical.
Sound like a real private conversation, not a podcast, newsreader, or support script.
Use plain spoken language. Short sentences are fine. Fragments are fine when they sound natural.
Usually ask one clear question at a time, but do not force a question if the next useful move is a statement.
Vary your first sentence. Do not repeatedly open with "It sounds like", "That sounds like", or similar reflective filler.
Prefer direct starts such as "Yeah, that is a lot.", "Start here:", "Let’s slow this down.", or a concise observation tied to the user’s exact words.
Use at most one brief validation sentence before moving to a practical next step or one clear question.
Continue from the recent conversation instead of restarting. If you already asked a question, respond to the user's answer before asking another.
Do not make every turn end with a new question. Sometimes reflect the thread, name the next step, or offer a short choice.
Avoid polished essay structure, generic coaching language, and repeated question patterns.
Do not encourage revenge, violence, dependency, shame, medical claims, or certainty in complex life problems.
If the user sounds overwhelmed, slow the pace and help them identify one safe next step."""


class OpenAIProvider:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    @property
    def enabled(self) -> bool:
        return self.client is not None and self.settings.ai_provider == "openai"

    @property
    def stt_enabled(self) -> bool:
        return self.client is not None and self.settings.stt_provider == "openai"

    @property
    def tts_enabled(self) -> bool:
        if self.settings.tts_provider == "openai":
            return self.client is not None
        if self.settings.tts_provider == "deepgram":
            return bool(self.settings.deepgram_api_key)
        return False

    def generate_response(
        self,
        message: str,
        mode: str,
        memory_block: str,
        guidance_block: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if not self.enabled:
            return generate_grounded_response(message, mode, memory_block, guidance_block)

        history_block = build_history_block(history or [])
        prompt = (
            f"Mode: {mode}\n\n"
            "Use the user memory and recent conversation below as context. Do not repeat them back unless useful. "
            "Continue naturally from the latest turn.\n\n"
            f"{memory_block}\n\n"
            f"{guidance_block}\n\n"
            f"{history_block}\n\n"
            f"User message:\n{message}"
        )
        try:
            responses = getattr(self.client, "responses", None)
            if responses is not None:
                response = responses.create(
                    model=self.settings.openai_chat_model,
                    instructions=CONVERSATION_INSTRUCTIONS,
                    input=prompt,
                    store=False,
                )
                output_text = getattr(response, "output_text", None)
                if output_text:
                    return output_text.strip()

            completion = self.client.chat.completions.create(
                model=self.settings.openai_chat_model,
                messages=[
                    {"role": "system", "content": CONVERSATION_INSTRUCTIONS},
                    {"role": "user", "content": prompt},
                ],
            )
            content = completion.choices[0].message.content
            if content:
                return content.strip()
        except Exception:
            return generate_grounded_response(message, mode, memory_block, guidance_block)

        return generate_grounded_response(message, mode, memory_block, guidance_block)

    def embed_text(self, text: str) -> list[float]:
        if not self.enabled:
            return stable_demo_embedding(text)
        try:
            result = self.client.embeddings.create(model=self.settings.openai_embedding_model, input=text)
            return list(result.data[0].embedding)
        except Exception:
            return stable_demo_embedding(text)

    def transcribe_audio(self, audio_path: str | Path) -> str:
        if not self.stt_enabled:
            raise RuntimeError("Voice transcription needs OPENAI_API_KEY")
        with Path(audio_path).open("rb") as audio_file:
            request = {
                "model": self.settings.openai_stt_model or self.settings.openai_transcription_model,
                "file": audio_file,
                "prompt": (
                    "Transcribe only clear speech from the audio. Keep the user's natural wording and language. "
                    "If there is no clear speech, return no text."
                ),
            }
            if self.settings.openai_stt_language:
                request["language"] = self.settings.openai_stt_language
            transcript = self.client.audio.transcriptions.create(**request)
        text = getattr(transcript, "text", "")
        return text.strip()

    def synthesize_speech(self, text: str) -> bytes:
        if not self.tts_enabled:
            raise RuntimeError("Text to speech needs a configured TTS provider API key")
        if self.settings.tts_provider == "deepgram":
            return self._synthesize_deepgram_speech(text)

        return self._synthesize_openai_speech(text)

    def _synthesize_openai_speech(self, text: str) -> bytes:
        request = {
            "model": self.settings.openai_tts_model,
            "voice": self.settings.openai_tts_voice,
            "input": text,
            "response_format": self.settings.openai_tts_response_format,
            "speed": self.settings.openai_tts_speed,
        }
        if self.settings.openai_tts_instructions:
            request["extra_body"] = {"instructions": self.settings.openai_tts_instructions}

        speech = self.client.audio.speech.create(**request)
        return bytes(speech.content)

    def _synthesize_deepgram_speech(self, text: str) -> bytes:
        query: dict[str, str] = {
            "model": self.settings.deepgram_tts_model,
            "encoding": self.settings.deepgram_tts_encoding,
            "speed": str(self.settings.deepgram_tts_speed),
        }
        if self.settings.deepgram_tts_container:
            query["container"] = self.settings.deepgram_tts_container
        if self.settings.deepgram_tts_sample_rate:
            query["sample_rate"] = str(self.settings.deepgram_tts_sample_rate)
        if self.settings.deepgram_tts_bitrate:
            query["bit_rate"] = str(self.settings.deepgram_tts_bitrate)

        url = f"{self.settings.deepgram_tts_base_url}?{urlencode(query)}"
        payload = json.dumps({"text": text}).encode("utf-8")
        request = Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Token {self.settings.deepgram_api_key}",
                "Content-Type": "application/json",
                "Accept": f"audio/{self.settings.deepgram_tts_encoding}",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                audio = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Deepgram TTS failed with HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Deepgram TTS network failed: {exc.reason}") from exc
        if not audio:
            raise RuntimeError("Deepgram TTS returned empty audio")
        return audio


def stable_demo_embedding(text: str, dimensions: int = 1536) -> list[float]:
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dimensions)]


def build_history_block(history: list[dict[str, str]]) -> str:
    if not history:
        return "Recent conversation: none"

    lines = []
    for item in history:
        role = item.get("role", "").strip().lower()
        text = item.get("text", "").strip()
        if role not in {"user", "forge", "assistant"} or not text:
            continue
        label = "Forge" if role in {"forge", "assistant"} else "User"
        lines.append(f"{label}: {text[:700]}")
    if not lines:
        return "Recent conversation: none"
    return "Recent conversation:\n" + "\n".join(lines)
