from __future__ import annotations

import hashlib
import random
from pathlib import Path

from openai import OpenAI

from app.config import Settings, get_settings
from app.services.ai import generate_grounded_response

CONVERSATION_INSTRUCTIONS = """You are ForgeMind, an AI mental health support companion for men.
You are not a therapist, doctor, emergency service, or diagnostic tool.
Tone: calm, direct, practical, private, grounded, emotionally safe, masculine-neutral, and non-clinical.
Usually ask one clear question at a time.
Do not encourage revenge, violence, dependency, shame, medical claims, or certainty in complex life problems.
If the user sounds overwhelmed, slow the pace and help them identify one safe next step."""


class OpenAIProvider:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def generate_response(self, message: str, mode: str, memory_block: str, guidance_block: str) -> str:
        if not self.client:
            return generate_grounded_response(message, mode, memory_block, guidance_block)

        prompt = (
            f"Mode: {mode}\n\n"
            f"{memory_block}\n\n"
            f"{guidance_block}\n\n"
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
        if not self.client:
            return stable_demo_embedding(text)
        try:
            result = self.client.embeddings.create(model=self.settings.openai_embedding_model, input=text)
            return list(result.data[0].embedding)
        except Exception:
            return stable_demo_embedding(text)

    def transcribe_audio(self, audio_path: str | Path) -> str:
        if not self.client:
            raise RuntimeError("Voice transcription needs OPENAI_API_KEY")
        with Path(audio_path).open("rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model=self.settings.openai_transcription_model,
                file=audio_file,
                prompt="ForgeMind voice journal. Preserve the user's natural wording.",
            )
        text = getattr(transcript, "text", "")
        return text.strip()


def stable_demo_embedding(text: str, dimensions: int = 1536) -> list[float]:
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(dimensions)]
