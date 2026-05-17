import asyncio
import tempfile
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from app.config import get_public_config
from app.schemas import (
    AuthRequest,
    AuthResponse,
    AuthUser,
    ChatRequest,
    ChatResponse,
    GuidanceCreate,
    GuidanceRule,
    MemoryListResponse,
    SafetyEventListResponse,
    SafetyLevel,
    SubscriptionValidationRequest,
    SubscriptionValidationResponse,
)
from app.services.ai import validate_response_safety
from app.services.auth import extract_bearer_token, issue_access_token, verify_access_token, verify_identity_token
from app.services.guidance import DEFAULT_GUIDANCE_RULES, build_guidance_prompt_block, retrieve_guidance
from app.services.memory import build_memory_prompt_block, extract_memory_candidates, filter_and_rank_memories
from app.services.openai_provider import OpenAIProvider
from app.services.observability import capture_event, configure_observability
from app.services import store
from app.services.safety import classify_safety
from app.services.subscription import validate_store_purchase

REQUEST_COUNT = Counter("forgemind_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("forgemind_http_request_seconds", "HTTP request latency", ["method", "path"])
SAFETY_EVENTS = Counter("forgemind_safety_events_total", "Safety events", ["level"])
MEMORY_RETRIEVAL_LATENCY = Histogram("forgemind_memory_retrieval_seconds", "Memory retrieval latency")
AI_LATENCY = Histogram("forgemind_ai_response_seconds", "AI response latency")

app = FastAPI(title="ForgeMind API", version="0.1.0")
configure_observability()

guidance_rules: dict[str, GuidanceRule] = {rule.id: rule for rule in DEFAULT_GUIDANCE_RULES}


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
def login(payload: AuthRequest) -> AuthResponse:
    try:
        user_id = verify_identity_token(payload.provider, payload.identity_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    async def _persist_user() -> None:
        await store.upsert_user(
            user_id=user_id,
            email=f"{payload.provider}-{user_id}@forgemind.local",
            display_name="ForgeMind User",
            provider=payload.provider.value,
            subject=payload.identity_token,
        )

    try:
        asyncio.run(_persist_user())
    except Exception:
        pass
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


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return _run_chat(payload)


async def _chat_flow(payload: ChatRequest, transcript: str | None = None) -> ChatResponse:
    safety = classify_safety(payload.message)
    SAFETY_EVENTS.labels(safety.level.value).inc()
    if safety.level == SafetyLevel.crisis:
        await _try_store_safety(payload.user_id, safety.level, safety.reasons)
        return ChatResponse(
            response=safety.crisis_response or "",
            safety_level=safety.level,
            memories_used=[],
            guidance_topics=[],
            transcript=transcript,
        )
    if safety.level == SafetyLevel.high:
        await _try_store_safety(payload.user_id, safety.level, safety.reasons)
        return ChatResponse(
            response=(
                "This sounds like a safety situation, not a normal coaching moment. "
                "If there is immediate danger, call emergency services now. If you can, "
                "move to a safer place and contact one trusted person nearby."
            ),
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
            memory_candidates = []

    memories = filter_and_rank_memories(memory_candidates)
    memory_block = build_memory_prompt_block(memories)

    db_guidance = list(guidance_rules.values())
    if db_available:
        try:
            await store.seed_default_guidance()
            db_guidance = await store.fetch_guidance_rules()
            persisted = True
        except Exception:
            db_guidance = list(guidance_rules.values())

    guidance = retrieve_guidance(payload.message, db_guidance)
    guidance_block = build_guidance_prompt_block(guidance)

    with AI_LATENCY.time():
        response = provider.generate_response(payload.message, payload.mode, memory_block, guidance_block)
    response_safety = validate_response_safety(response)
    if response_safety.value in {SafetyLevel.high.value, SafetyLevel.crisis.value}:
        raise HTTPException(status_code=500, detail="Generated response failed safety validation")

    try:
        if not db_available:
            raise RuntimeError("database unavailable")
        await store.ensure_demo_user(payload.user_id)
        session_id = await store.create_chat_session(payload.user_id, payload.mode)
        user_message_id = await store.save_chat_message(session_id, payload.user_id, "user", payload.message, safety.level)
        await store.save_chat_message(session_id, payload.user_id, "assistant", response, response_safety)
        if safety.level != SafetyLevel.low:
            await store.log_safety_event(payload.user_id, safety.level, safety.reasons, user_message_id)
        memory_contents = extract_memory_candidates(payload.message)
        memory_embeddings = {content: provider.embed_text(content) for content in memory_contents}
        await store.insert_memories(payload.user_id, memory_contents, memory_embeddings)
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
        persisted = False

    return ChatResponse(
        response=response,
        safety_level=safety.level,
        memories_used=[memory.id for memory in memories],
        guidance_topics=[rule.topic for rule in guidance],
        transcript=transcript,
        persisted=persisted,
    )


def _run_chat(payload: ChatRequest, transcript: str | None = None) -> ChatResponse:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_chat_flow(payload, transcript))
    raise RuntimeError("Use _chat_flow from async contexts")


async def _try_store_safety(user_id: str, level: SafetyLevel, reasons: list[str]) -> None:
    try:
        await store.ensure_demo_user(user_id)
        await store.log_safety_event(user_id, level, reasons)
    except Exception:
        return


@app.post("/voice-chat", response_model=ChatResponse)
async def voice_chat(
    user_id: str = Form(...),
    mode: str = Form("think_clearly"),
    audio: UploadFile = File(...),
) -> ChatResponse:
    provider = OpenAIProvider()
    if not provider.enabled:
        raise HTTPException(status_code=503, detail="Voice transcription needs OPENAI_API_KEY")

    suffix = ".m4a" if not audio.filename else "." + audio.filename.rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(suffix=suffix) as temporary:
        temporary.write(await audio.read())
        temporary.flush()
        try:
            transcript = provider.transcribe_audio(temporary.name)
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Voice transcription failed") from exc

    if not transcript:
        raise HTTPException(status_code=422, detail="No speech detected")
    return await _chat_flow(ChatRequest(user_id=user_id, message=transcript, mode=mode), transcript=transcript)


@app.post("/safety/classify")
def safety_classify(payload: ChatRequest):
    result = classify_safety(payload.message)
    SAFETY_EVENTS.labels(result.level.value).inc()
    return result


@app.get("/safety/events", response_model=SafetyEventListResponse)
def list_safety_events() -> SafetyEventListResponse:
    async def _list() -> SafetyEventListResponse:
        try:
            return SafetyEventListResponse(items=await store.list_safety_events())
        except Exception:
            return SafetyEventListResponse(items=[])

    return asyncio.run(_list())


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
def list_memories(user_id: str) -> MemoryListResponse:
    async def _list() -> MemoryListResponse:
        try:
            return MemoryListResponse(items=await store.list_user_memories(user_id))
        except Exception:
            return MemoryListResponse(items=[])

    return asyncio.run(_list())


@app.post("/subscriptions/validate", response_model=SubscriptionValidationResponse)
def validate_subscription(payload: SubscriptionValidationRequest) -> SubscriptionValidationResponse:
    result = validate_store_purchase(payload.user_id, payload.platform, payload.receipt_or_purchase_token)

    async def _persist() -> bool:
        await store.save_subscription_validation(
            user_id=result.user_id,
            platform=result.platform,
            entitlement=result.entitlement,
            valid=result.valid,
            store_transaction_id=payload.receipt_or_purchase_token,
        )
        return True

    try:
        result.persisted = asyncio.run(_persist())
    except Exception:
        result.persisted = False
    capture_event(
        "subscription_validation",
        {"user_id": result.user_id, "platform": result.platform, "valid": result.valid},
    )
    return result


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
