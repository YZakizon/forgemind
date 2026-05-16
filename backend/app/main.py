from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from app.config import get_public_config
from app.schemas import (
    AuthRequest,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    GuidanceCreate,
    GuidanceRule,
    SafetyLevel,
    SubscriptionValidationRequest,
    SubscriptionValidationResponse,
)
from app.services.ai import generate_grounded_response, validate_response_safety
from app.services.auth import issue_access_token, verify_identity_token
from app.services.guidance import DEFAULT_GUIDANCE_RULES, build_guidance_prompt_block, retrieve_guidance
from app.services.memory import build_memory_prompt_block, filter_and_rank_memories
from app.services.safety import classify_safety
from app.services.subscription import validate_store_purchase

REQUEST_COUNT = Counter("forgemind_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("forgemind_http_request_seconds", "HTTP request latency", ["method", "path"])
SAFETY_EVENTS = Counter("forgemind_safety_events_total", "Safety events", ["level"])
MEMORY_RETRIEVAL_LATENCY = Histogram("forgemind_memory_retrieval_seconds", "Memory retrieval latency")
AI_LATENCY = Histogram("forgemind_ai_response_seconds", "AI response latency")

app = FastAPI(title="ForgeMind API", version="0.1.0")

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
    return AuthResponse(user_id=user_id, access_token=issue_access_token(user_id))


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    safety = classify_safety(payload.message)
    SAFETY_EVENTS.labels(safety.level.value).inc()
    if safety.level == SafetyLevel.crisis:
        return ChatResponse(
            response=safety.crisis_response or "",
            safety_level=safety.level,
            memories_used=[],
            guidance_topics=[],
        )

    with MEMORY_RETRIEVAL_LATENCY.time():
        memories = filter_and_rank_memories([])
        memory_block = build_memory_prompt_block(memories)
    guidance = retrieve_guidance(payload.message, list(guidance_rules.values()))
    guidance_block = build_guidance_prompt_block(guidance)
    with AI_LATENCY.time():
        response = generate_grounded_response(payload.message, payload.mode, memory_block, guidance_block)
    response_safety = validate_response_safety(response)
    if response_safety.value in {SafetyLevel.high.value, SafetyLevel.crisis.value}:
        raise HTTPException(status_code=500, detail="Generated response failed safety validation")
    return ChatResponse(
        response=response,
        safety_level=safety.level,
        memories_used=[memory.id for memory in memories],
        guidance_topics=[rule.topic for rule in guidance],
    )


@app.post("/safety/classify")
def safety_classify(payload: ChatRequest):
    result = classify_safety(payload.message)
    SAFETY_EVENTS.labels(result.level.value).inc()
    return result


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


@app.get("/memories")
def list_memories() -> dict[str, list[dict]]:
    return {"items": []}


@app.post("/subscriptions/validate", response_model=SubscriptionValidationResponse)
def validate_subscription(payload: SubscriptionValidationRequest) -> SubscriptionValidationResponse:
    return validate_store_purchase(payload.user_id, payload.platform, payload.receipt_or_purchase_token)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")
