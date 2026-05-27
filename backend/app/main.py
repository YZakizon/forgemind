import asyncio
import base64
import json
import logging
import re
import tempfile
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response, StreamingResponse

from app.config import get_public_config
from app.schemas import (
    AuthRequest,
    AuthResponse,
    AuthUser,
    ChatRequest,
    ChatResponse,
    ChatResponseParts,
    DataControlResponse,
    GuidanceCreate,
    GuidanceRule,
    MemoryListResponse,
    MoodCheckin,
    MoodCheckinCreate,
    ProfileFactPolicy,
    ProfileFactPolicyUpdate,
    ProgressSummary,
    ResetSession,
    ResetSessionCreate,
    ReplySuggestionsRequest,
    ReplySuggestionsResponse,
    SafetyEventListResponse,
    SafetyLevel,
    SpeechRequest,
    SubscriptionValidationRequest,
    SubscriptionValidationResponse,
    UserDataExport,
)
from app.services.ai import validate_response_safety
from app.services.auth import extract_bearer_token, issue_access_token, verify_access_token, verify_identity_token
from app.services.guidance import DEFAULT_GUIDANCE_RULES, build_guidance_prompt_block, retrieve_guidance
from app.services.memory import build_memory_prompt_block, extract_memory_candidates, filter_and_rank_memories
from app.services.profile_facts import build_profile_facts_prompt_block, extract_profile_facts
from app.services.openai_provider import OpenAIProvider
from app.services.observability import capture_event, configure_observability
from app.services import store
from app.services.safety import classify_safety
from app.services.subscription import validate_store_purchase

logger = logging.getLogger("forgemind.api")

REQUEST_COUNT = Counter("forgemind_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("forgemind_http_request_seconds", "HTTP request latency", ["method", "path"])
SAFETY_EVENTS = Counter("forgemind_safety_events_total", "Safety events", ["level"])
MEMORY_RETRIEVAL_LATENCY = Histogram("forgemind_memory_retrieval_seconds", "Memory retrieval latency")
AI_LATENCY = Histogram("forgemind_ai_response_seconds", "AI response latency")
TTS_LATENCY = Histogram("forgemind_tts_seconds", "Text to speech latency")

app = FastAPI(title="ForgeMind API", version="0.1.0")
configure_observability()

guidance_rules: dict[str, GuidanceRule] = {rule.id: rule for rule in DEFAULT_GUIDANCE_RULES}


@dataclass
class VoiceTranscriptSegment:
    index: int
    text: str
    started_at_ms: int | None = None
    ended_at_ms: int | None = None


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(perf_counter() - start)
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/config")
def config():
    return get_public_config()


@app.post("/auth/login", response_model=AuthResponse)
async def login(payload: AuthRequest) -> AuthResponse:
    try:
        user_id = verify_identity_token(payload.provider, payload.identity_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        await store.upsert_user(
            user_id=user_id,
            email=f"{payload.provider}-{user_id}@forgemind.local",
            display_name="ForgeMind User",
            provider=payload.provider.value,
            subject=payload.identity_token,
        )
    except Exception:
        logger.exception("auth user persistence failed", extra={"user_id": user_id, "provider": payload.provider.value})
    capture_event("auth_login", {"user_id": user_id, "provider": payload.provider.value})
    return AuthResponse(user_id=user_id, access_token=issue_access_token(user_id))


@app.get("/auth/me", response_model=AuthUser)
def auth_me(authorization: str | None = Header(default=None)) -> AuthUser:
    try:
        token = extract_bearer_token(authorization)
        user_id = verify_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return AuthUser(user_id=user_id)


def _require_user_access(user_id: str, authorization: str | None) -> None:
    try:
        token = extract_bearer_token(authorization)
        token_user_id = verify_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if token_user_id != user_id:
        raise HTTPException(status_code=403, detail="access token does not match requested user")


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    return await _chat_flow(payload)


@app.post("/reply-suggestions", response_model=ReplySuggestionsResponse)
async def reply_suggestions(payload: ReplySuggestionsRequest) -> ReplySuggestionsResponse:
    provider = OpenAIProvider()
    suggestions = provider.generate_reply_suggestions(
        user_message=payload.user_message,
        forge_message=payload.forge_message,
        mode=payload.mode,
        history=payload.history,
    )
    return ReplySuggestionsResponse(suggestions=suggestions[:3])


@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest) -> StreamingResponse:
    async def events():
        try:
            response = await _chat_flow(payload)
            yield _sse("response", response.model_dump(mode="json"))
            yield _sse("done", {"ok": True})
        except HTTPException as exc:
            yield _sse("error", {"detail": exc.detail, "status_code": exc.status_code})
        except Exception:
            logger.exception("chat stream failed", extra={"user_id": payload.user_id})
            yield _sse("error", {"detail": "Chat failed", "status_code": 500})

    return StreamingResponse(events(), media_type="text/event-stream")


async def _chat_flow(payload: ChatRequest, transcript: str | None = None) -> ChatResponse:
    safety = classify_safety(payload.message)
    SAFETY_EVENTS.labels(safety.level.value).inc()
    if safety.level == SafetyLevel.crisis:
        await _try_store_safety(payload.user_id, safety.level, safety.reasons)
        crisis_response = safety.crisis_response or ""
        return ChatResponse(
            response=crisis_response,
            response_parts=split_response_parts(crisis_response),
            safety_level=safety.level,
            memories_used=[],
            guidance_topics=[],
            transcript=transcript,
        )
    if safety.level == SafetyLevel.high:
        await _try_store_safety(payload.user_id, safety.level, safety.reasons)
        high_response = (
            "This sounds like a safety situation, not a normal coaching moment. "
            "If there is immediate danger, call emergency services now. If you can, "
            "move to a safer place and contact one trusted person nearby."
        )
        return ChatResponse(
            response=high_response,
            response_parts=split_response_parts(high_response),
            safety_level=safety.level,
            memories_used=[],
            guidance_topics=[],
            transcript=transcript,
        )

    provider = OpenAIProvider()
    persisted = False
    db_available = False
    with MEMORY_RETRIEVAL_LATENCY.time():
        memory_candidates = []
        try:
            await store.ensure_demo_user(payload.user_id)
            query_embedding = provider.embed_text(payload.message)
            memory_candidates = await store.retrieve_memory_candidates(payload.user_id, query_embedding)
            persisted = True
            db_available = True
        except Exception:
            logger.exception("memory retrieval failed", extra={"user_id": payload.user_id})
            memory_candidates = []

    memories = filter_and_rank_memories(memory_candidates)
    memory_block = build_memory_prompt_block(memories)
    profile_fact_block = build_profile_facts_prompt_block([])
    if db_available:
        try:
            profile_fact_block = build_profile_facts_prompt_block(await store.list_user_profile_facts(payload.user_id))
        except Exception:
            logger.exception("profile fact retrieval failed", extra={"user_id": payload.user_id})

    db_guidance = list(guidance_rules.values())
    if db_available:
        try:
            await store.seed_default_guidance()
            db_guidance = await store.fetch_guidance_rules()
            persisted = True
        except Exception:
            logger.exception("guidance retrieval failed", extra={"user_id": payload.user_id})
            db_guidance = list(guidance_rules.values())

    guidance = retrieve_guidance(payload.message, db_guidance)
    guidance_block = build_guidance_prompt_block(guidance)

    with AI_LATENCY.time():
        response = provider.generate_response(payload.message, payload.mode, memory_block, guidance_block, profile_fact_block, payload.history)
    response_safety = validate_response_safety(response)
    if response_safety.value in {SafetyLevel.high.value, SafetyLevel.crisis.value}:
        raise HTTPException(status_code=500, detail="Generated response failed safety validation")

    try:
        if not db_available:
            raise RuntimeError("database unavailable")
        await store.ensure_demo_user(payload.user_id)
        profile_fact_policy = await store.get_profile_fact_policy()
        session_id = await store.create_chat_session(payload.user_id, payload.mode)
        user_message_id = await store.save_chat_message(session_id, payload.user_id, "user", payload.message, safety.level)
        await store.save_chat_message(session_id, payload.user_id, "assistant", response, response_safety)
        if safety.level != SafetyLevel.low:
            await store.log_safety_event(payload.user_id, safety.level, safety.reasons, user_message_id)
        memory_contents = extract_memory_candidates(payload.message)
        memory_embeddings = {content: provider.embed_text(content) for content in memory_contents}
        await store.insert_memories(payload.user_id, memory_contents, memory_embeddings)
        profile_facts = extract_profile_facts(payload.message, policy=profile_fact_policy)
        profile_facts.extend(provider.extract_profile_facts(payload.message, policy=profile_fact_policy))
        await store.insert_profile_facts(payload.user_id, profile_facts)
        persisted = True
        capture_event(
            "chat_completed",
            {
                "user_id": payload.user_id,
                "mode": payload.mode,
                "safety_level": safety.level.value,
                "guidance_topics": [rule.topic for rule in guidance],
                "memories_used": len(memories),
                "memories_saved": len(memory_contents),
            },
        )
    except Exception:
        logger.exception("chat persistence failed", extra={"user_id": payload.user_id})
        persisted = False

    return ChatResponse(
        response=response,
        response_parts=split_response_parts(response),
        safety_level=safety.level,
        memories_used=[memory.id for memory in memories],
        guidance_topics=[rule.topic for rule in guidance],
        transcript=transcript,
        persisted=persisted,
    )


def split_response_parts(response: str) -> ChatResponseParts:
    text = " ".join(response.split())
    question_mark = text.rfind("?")
    if question_mark == -1:
        return ChatResponseParts(body=text)

    question_start = max(text.rfind(".", 0, question_mark), text.rfind("!", 0, question_mark), text.rfind("\n", 0, question_mark)) + 1
    question = text[question_start : question_mark + 1].strip()
    body = (text[:question_start] + text[question_mark + 1 :]).strip()
    body = drop_leading_question_sentences(body)
    if not body or len(question.split()) < 3:
        return ChatResponseParts(body=text)
    return ChatResponseParts(body=body, question=question)


def drop_leading_question_sentences(text: str) -> str:
    cleaned = text.strip()
    while cleaned:
        question_mark = cleaned.find("?")
        if question_mark == -1:
            return cleaned
        first_stop_candidates = [index for index in [cleaned.find("."), cleaned.find("!")] if index != -1]
        first_stop = min(first_stop_candidates) if first_stop_candidates else -1
        if first_stop != -1 and first_stop < question_mark:
            return cleaned
        remainder = cleaned[question_mark + 1 :].strip()
        if not remainder:
            return text.strip()
        cleaned = remainder
    return cleaned


def merge_transcript_segments(segments: list[VoiceTranscriptSegment], clean_punctuation: bool = True) -> str:
    merged = ""
    for segment in sorted(segments, key=lambda item: item.index):
        text = " ".join(segment.text.split())
        if is_empty_or_prompt_echo_transcript(text):
            text = ""
        if not text:
            continue
        if not merged:
            merged = text
            continue
        merged = merge_overlapping_text(merged, text)
    return clean_transcript_punctuation(merged) if clean_punctuation else merged


def merge_overlapping_text(current: str, next_text: str, max_overlap_words: int = 14) -> str:
    current_words = current.split()
    next_words = next_text.split()
    max_overlap = min(max_overlap_words, len(current_words), len(next_words))
    for size in range(max_overlap, 0, -1):
        if normalize_words(current_words[-size:]) == normalize_words(next_words[:size]):
            remainder = " ".join(next_words[size:])
            return current if not remainder else f"{current} {remainder}"
    return f"{current} {next_text}"


def normalize_words(words: list[str]) -> list[str]:
    return [word.strip(".,!?;:\"'()[]{}").casefold() for word in words]


def clean_transcript_punctuation(text: str) -> str:
    cleaned = " ".join(text.split())
    for punctuation in [".", ",", "!", "?", ";", ":"]:
        cleaned = cleaned.replace(f" {punctuation}", punctuation)
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def is_empty_or_prompt_echo_transcript(text: str) -> bool:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return True
    prompt_echoes = {
        "preserve the user's natural wording",
        "preserve the users natural wording",
        "preserve users natural wording",
        "preserve user natural wording",
        "keep the user's natural wording and language",
        "keep the users natural wording and language",
        "transcribe in the same language the user is speaking",
        "forgemind voice journal",
    }
    normalized_words = normalize_words(normalized.split())
    normalized_compact = " ".join(normalized_words)
    return any(echo in normalized_compact for echo in prompt_echoes)


def split_tts_chunks(text: str, max_chars: int = 180) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    if not sentences:
        return [normalized]

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_long_tts_sentence(sentence, max_chars))
            continue
        next_chunk = f"{current} {sentence}".strip() if current else sentence
        if current and len(next_chunk) > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = next_chunk
    if current:
        chunks.append(current)
    return chunks


def split_long_tts_sentence(sentence: str, max_chars: int) -> list[str]:
    words = sentence.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        next_chunk = f"{current} {word}".strip() if current else word
        if current and len(next_chunk) > max_chars:
            chunks.append(current)
            current = word
        else:
            current = next_chunk
    if current:
        chunks.append(current)
    return chunks


async def _try_store_safety(user_id: str, level: SafetyLevel, reasons: list[str]) -> None:
    try:
        await store.ensure_demo_user(user_id)
        await store.log_safety_event(user_id, level, reasons)
    except Exception:
        logger.exception("safety event persistence failed", extra={"user_id": user_id, "level": level.value})
        return


async def _transcribe_uploaded_audio(audio: UploadFile) -> str:
    suffix = ".m4a" if not audio.filename else "." + audio.filename.rsplit(".", 1)[-1]
    return await _transcribe_audio_bytes(await audio.read(), suffix)


async def _transcribe_audio_bytes(audio: bytes, suffix: str = ".m4a") -> str:
    provider = OpenAIProvider()
    if not provider.stt_enabled:
        raise HTTPException(status_code=503, detail="Voice transcription needs OPENAI_API_KEY")

    with tempfile.NamedTemporaryFile(suffix=suffix) as temporary:
        temporary.write(audio)
        temporary.flush()
        try:
            transcript = provider.transcribe_audio(temporary.name)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Voice transcription failed") from exc

    if is_empty_or_prompt_echo_transcript(transcript):
        raise HTTPException(status_code=422, detail="No speech detected")
    return transcript


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def _ws_send(websocket: WebSocket, event_type: str, payload: dict | None = None) -> None:
    await websocket.send_json({"type": event_type, **(payload or {})})


async def _ws_send_tts_audio(websocket: WebSocket, part: str, text: str, chunk_index: int = 0, chunk_total: int = 1) -> None:
    provider = OpenAIProvider()
    if not provider.tts_enabled:
        return
    try:
        with TTS_LATENCY.time():
            audio = await asyncio.to_thread(provider.synthesize_speech, text)
    except Exception:
        logger.exception("voice websocket tts failed", extra={"part": part})
        return
    await _ws_send(
        websocket,
        "tts_audio",
        {
            "part": part,
            "text": text,
            "chunk_index": chunk_index,
            "chunk_total": chunk_total,
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "format": speech_response_format(provider),
            "media_type": speech_media_type(provider),
        },
    )


@app.websocket("/voice/ws")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    user_id = "00000000-0000-4000-8000-000000000001"
    mode = "think_clearly"
    history: list[dict[str, str]] = []
    buffered_transcripts: dict[int, VoiceTranscriptSegment] = {}

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "start":
                user_id = str(message.get("user_id") or user_id)
                mode = str(message.get("mode") or mode)
                raw_history = message.get("history")
                history = raw_history if isinstance(raw_history, list) else []
                buffered_transcripts = {}
                await _ws_send(websocket, "ready")
                continue

            if message_type == "audio_chunk":
                chunk_index = int(message.get("index") or len(buffered_transcripts))
                audio_base64 = message.get("audio_base64")
                if not isinstance(audio_base64, str) or not audio_base64:
                    await _ws_send(websocket, "error", {"detail": "Missing audio chunk"})
                    continue
                try:
                    audio = base64.b64decode(audio_base64)
                    suffix = str(message.get("suffix") or ".m4a")
                    transcript = await _transcribe_audio_bytes(audio, suffix if suffix.startswith(".") else f".{suffix}")
                except HTTPException as exc:
                    if exc.status_code == 422:
                        buffered_transcripts[chunk_index] = VoiceTranscriptSegment(
                            index=chunk_index,
                            text="",
                            started_at_ms=message.get("started_at_ms"),
                            ended_at_ms=message.get("ended_at_ms"),
                        )
                        await _ws_send(websocket, "transcript", {"index": chunk_index, "text": ""})
                        continue
                    await _ws_send(websocket, "error", {"detail": exc.detail, "status_code": exc.status_code})
                    continue
                segment = VoiceTranscriptSegment(
                    index=chunk_index,
                    text=transcript,
                    started_at_ms=message.get("started_at_ms"),
                    ended_at_ms=message.get("ended_at_ms"),
                )
                buffered_transcripts[chunk_index] = segment
                await _ws_send(
                    websocket,
                    "transcript",
                    {
                        "index": chunk_index,
                        "text": transcript,
                        "started_at_ms": segment.started_at_ms,
                        "ended_at_ms": segment.ended_at_ms,
                    },
                )
                continue

            if message_type == "stop":
                transcript = merge_transcript_segments(list(buffered_transcripts.values()))
                if not transcript:
                    await _ws_send(websocket, "error", {"detail": "No speech detected", "status_code": 422})
                    await _ws_send(websocket, "done")
                    buffered_transcripts = {}
                    continue

                await _ws_send(
                    websocket,
                    "final_transcript",
                    {
                        "text": transcript,
                        "segments": [
                            {
                                "index": segment.index,
                                "text": segment.text,
                                "started_at_ms": segment.started_at_ms,
                                "ended_at_ms": segment.ended_at_ms,
                            }
                            for segment in sorted(buffered_transcripts.values(), key=lambda item: item.index)
                        ],
                    },
                )
                response = await _chat_flow(ChatRequest(user_id=user_id, message=transcript, mode=mode, history=history), transcript=transcript)
                parts = response.response_parts or split_response_parts(response.response)
                body_chunks = split_tts_chunks(parts.body)
                for index, chunk in enumerate(body_chunks):
                    await _ws_send_tts_audio(websocket, "body", chunk, index, len(body_chunks))
                    await _ws_send(websocket, "response_part", {"part": "body", "text": chunk, "chunk_index": index, "chunk_total": len(body_chunks)})
                if parts.question:
                    await _ws_send_tts_audio(websocket, "question", parts.question, 0, 1)
                    await _ws_send(websocket, "response_part", {"part": "question", "text": parts.question, "chunk_index": 0, "chunk_total": 1})
                await _ws_send(websocket, "response", {"payload": response.model_dump(mode="json")})
                await _ws_send(websocket, "done")
                buffered_transcripts = {}
                continue

            await _ws_send(websocket, "error", {"detail": f"Unknown voice event: {message_type}"})
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("voice websocket failed", extra={"user_id": user_id})
        await _ws_send(websocket, "error", {"detail": "Voice chat failed", "status_code": 500})


@app.post("/voice-chat", response_model=ChatResponse)
async def voice_chat(
    user_id: str = Form(...),
    mode: str = Form("think_clearly"),
    audio: UploadFile = File(...),
) -> ChatResponse:
    transcript = await _transcribe_uploaded_audio(audio)
    return await _chat_flow(ChatRequest(user_id=user_id, message=transcript, mode=mode), transcript=transcript)


@app.post("/voice-transcribe")
async def voice_transcribe(audio: UploadFile = File(...)) -> dict[str, str]:
    transcript = await _transcribe_uploaded_audio(audio)
    return {"transcript": transcript}


@app.post("/voice-chat/stream")
async def voice_chat_stream(
    user_id: str = Form(...),
    mode: str = Form("think_clearly"),
    audio: UploadFile = File(...),
) -> StreamingResponse:
    async def events():
        try:
            transcript = await _transcribe_uploaded_audio(audio)
            yield _sse("transcript", {"transcript": transcript})
            response = await _chat_flow(ChatRequest(user_id=user_id, message=transcript, mode=mode), transcript=transcript)
            yield _sse("response", response.model_dump(mode="json"))
            yield _sse("done", {"ok": True})
        except HTTPException as exc:
            yield _sse("error", {"detail": exc.detail, "status_code": exc.status_code})
        except Exception:
            logger.exception("voice chat stream failed", extra={"user_id": user_id})
            yield _sse("error", {"detail": "Voice chat failed", "status_code": 500})

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/speech")
def speech(payload: SpeechRequest) -> Response:
    provider = OpenAIProvider()
    if not provider.tts_enabled:
        raise HTTPException(status_code=503, detail="Text to speech needs a configured TTS provider API key")

    try:
        with TTS_LATENCY.time():
            audio = provider.synthesize_speech(payload.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Text to speech failed") from exc

    return Response(
        content=audio,
        media_type=speech_media_type(provider),
        headers={"Cache-Control": "no-store"},
    )


def speech_media_type(provider: OpenAIProvider) -> str:
    response_format = speech_response_format(provider)
    if response_format == "mp3":
        return "audio/mpeg"
    return f"audio/{response_format}"


def speech_response_format(provider: OpenAIProvider) -> str:
    if provider.settings.tts_provider == "deepgram":
        return provider.settings.deepgram_tts_encoding
    return provider.settings.openai_tts_response_format


@app.post("/safety/classify")
def safety_classify(payload: ChatRequest):
    result = classify_safety(payload.message)
    SAFETY_EVENTS.labels(result.level.value).inc()
    return result


@app.get("/safety/events", response_model=SafetyEventListResponse)
async def list_safety_events() -> SafetyEventListResponse:
    try:
        return SafetyEventListResponse(items=await store.list_safety_events())
    except Exception:
        logger.exception("list safety events failed")
        return SafetyEventListResponse(items=[])


@app.get("/guidance/rules", response_model=list[GuidanceRule])
def list_guidance_rules() -> list[GuidanceRule]:
    return list(guidance_rules.values())


@app.post("/guidance/rules", response_model=GuidanceRule)
def create_guidance_rule(payload: GuidanceCreate) -> GuidanceRule:
    rule = GuidanceRule(id=str(uuid4()), **payload.model_dump())
    guidance_rules[rule.id] = rule
    return rule


@app.put("/guidance/rules/{rule_id}", response_model=GuidanceRule)
def update_guidance_rule(rule_id: str, payload: GuidanceCreate) -> GuidanceRule:
    if rule_id not in guidance_rules:
        raise HTTPException(status_code=404, detail="Guidance rule not found")
    rule = GuidanceRule(id=rule_id, **payload.model_dump())
    guidance_rules[rule_id] = rule
    return rule


@app.delete("/guidance/rules/{rule_id}")
def delete_guidance_rule(rule_id: str) -> dict[str, str]:
    if rule_id not in guidance_rules:
        raise HTTPException(status_code=404, detail="Guidance rule not found")
    del guidance_rules[rule_id]
    return {"status": "deleted"}


@app.get("/memories", response_model=MemoryListResponse)
async def list_memories(user_id: str) -> MemoryListResponse:
    try:
        return MemoryListResponse(items=await store.list_user_memories(user_id))
    except Exception:
        logger.exception("list memories failed", extra={"user_id": user_id})
        return MemoryListResponse(items=[])


@app.get("/profile-facts/policy", response_model=ProfileFactPolicy)
async def get_profile_fact_policy() -> ProfileFactPolicy:
    try:
        return await store.get_profile_fact_policy()
    except Exception:
        logger.exception("get profile fact policy failed")
        return ProfileFactPolicy()


@app.put("/profile-facts/policy", response_model=ProfileFactPolicy)
async def update_profile_fact_policy(payload: ProfileFactPolicyUpdate) -> ProfileFactPolicy:
    try:
        return await store.save_profile_fact_policy(payload)
    except Exception as exc:
        logger.exception("update profile fact policy failed")
        raise HTTPException(status_code=503, detail="Profile fact policy is unavailable") from exc


@app.post("/memories/archive", response_model=DataControlResponse)
async def archive_memories(user_id: str, authorization: str | None = Header(default=None)) -> DataControlResponse:
    _require_user_access(user_id, authorization)

    try:
        archived = await store.archive_user_memories(user_id)
        capture_event("memories_archived", {"user_id": user_id, "count": archived})
        return DataControlResponse(user_id=user_id, status="archived", detail=f"Archived {archived} active memories.")
    except Exception as exc:
        logger.exception("memory archive failed", extra={"user_id": user_id})
        raise HTTPException(status_code=503, detail="Memory archive is unavailable") from exc


@app.get("/users/{user_id}/export", response_model=UserDataExport)
async def export_user_data(user_id: str, authorization: str | None = Header(default=None)) -> UserDataExport:
    _require_user_access(user_id, authorization)

    try:
        result = await store.export_user_data(user_id)
        capture_event("user_data_exported", {"user_id": user_id})
        return result
    except Exception as exc:
        logger.exception("user data export failed", extra={"user_id": user_id})
        raise HTTPException(status_code=503, detail="Data export is unavailable") from exc


@app.delete("/users/{user_id}/data", response_model=DataControlResponse)
async def delete_user_data(user_id: str, authorization: str | None = Header(default=None)) -> DataControlResponse:
    _require_user_access(user_id, authorization)

    try:
        await store.delete_user_data(user_id)
        capture_event("user_data_deleted", {"user_id": user_id})
        return DataControlResponse(user_id=user_id, status="deleted", detail="Deleted stored chat, memory, check-in, reset, subscription, and safety data.")
    except Exception as exc:
        logger.exception("user data deletion failed", extra={"user_id": user_id})
        raise HTTPException(status_code=503, detail="Data deletion is unavailable") from exc


@app.post("/mood-checkins", response_model=MoodCheckin)
async def create_mood_checkin(payload: MoodCheckinCreate) -> MoodCheckin:
    try:
        result = await store.create_mood_checkin(payload.user_id, payload.label, payload.intensity, payload.note)
        capture_event("mood_checkin_created", {"user_id": payload.user_id, "label": payload.label})
        return result
    except Exception as exc:
        logger.exception("mood check-in storage failed", extra={"user_id": payload.user_id, "label": payload.label})
        raise HTTPException(status_code=503, detail="Mood check-in storage is unavailable") from exc


@app.post("/reset-sessions", response_model=ResetSession)
async def create_reset_session(payload: ResetSessionCreate) -> ResetSession:
    try:
        result = await store.create_reset_session(payload.user_id, payload.reset_type, payload.notes)
        capture_event("reset_session_started", {"user_id": payload.user_id, "reset_type": payload.reset_type})
        return result
    except Exception as exc:
        logger.exception("reset session creation failed", extra={"user_id": payload.user_id, "reset_type": payload.reset_type})
        raise HTTPException(status_code=503, detail="Reset session storage is unavailable") from exc


@app.post("/reset-sessions/{reset_id}/complete", response_model=ResetSession)
async def complete_reset_session(reset_id: str, user_id: str) -> ResetSession:
    try:
        result = await store.complete_reset_session(reset_id, user_id)
        capture_event("reset_session_completed", {"user_id": user_id, "reset_type": result.reset_type})
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("reset session completion failed", extra={"user_id": user_id, "reset_id": reset_id})
        raise HTTPException(status_code=503, detail="Reset session storage is unavailable") from exc


@app.get("/progress/summary", response_model=ProgressSummary)
async def progress_summary(user_id: str) -> ProgressSummary:
    try:
        return await store.get_progress_summary(user_id)
    except Exception:
        logger.exception("progress summary failed", extra={"user_id": user_id})
        return ProgressSummary(user_id=user_id)


@app.post("/subscriptions/validate", response_model=SubscriptionValidationResponse)
async def validate_subscription(payload: SubscriptionValidationRequest) -> SubscriptionValidationResponse:
    result = validate_store_purchase(payload.user_id, payload.platform, payload.receipt_or_purchase_token, payload.product_id)

    try:
        await store.save_subscription_validation(
            user_id=result.user_id,
            platform=result.platform,
            entitlement=result.entitlement,
            valid=result.valid,
            store_transaction_id=payload.receipt_or_purchase_token,
        )
        result.persisted = True
    except Exception:
        logger.exception("subscription validation persistence failed", extra={"user_id": result.user_id, "platform": result.platform})
        result.persisted = False
    capture_event(
        "subscription_validation",
        {"user_id": result.user_id, "platform": result.platform, "valid": result.valid},
    )
    return result


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
