from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class SafetyLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    crisis = "crisis"


class MemoryStatus(StrEnum):
    active = "active"
    inactive = "inactive"
    archived = "archived"


class AuthProvider(StrEnum):
    google = "google"
    apple = "apple"


class AuthRequest(BaseModel):
    provider: AuthProvider
    identity_token: str = Field(min_length=8)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


class ChatRequest(BaseModel):
    user_id: str
    message: str = Field(min_length=1, max_length=4000)
    mode: str = "think_clearly"


class ChatResponse(BaseModel):
    response: str
    safety_level: SafetyLevel
    memories_used: list[str] = []
    guidance_topics: list[str] = []


class MemoryCandidate(BaseModel):
    id: str
    user_id: str
    type: str
    content: str
    status: MemoryStatus = MemoryStatus.active
    importance: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    similarity: float = Field(ge=0, le=1)
    unsafe: bool = False
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    expires_at: datetime | None = None


class RankedMemory(MemoryCandidate):
    recency_score: float
    active_score: float
    final_score: float


class GuidanceRule(BaseModel):
    id: str
    topic: str
    tags: list[str] = []
    goal: str
    do_rules: list[str] = []
    avoid_rules: list[str] = []
    tone: str = "calm, direct, practical"
    safety_level: SafetyLevel = SafetyLevel.low
    priority: int = 0
    approved_by: str | None = None
    active: bool = True


class GuidanceCreate(BaseModel):
    topic: str
    tags: list[str] = []
    goal: str
    do_rules: list[str] = []
    avoid_rules: list[str] = []
    tone: str = "calm, direct, practical"
    safety_level: SafetyLevel = SafetyLevel.low
    priority: int = 0
    approved_by: str | None = None


class SafetyResult(BaseModel):
    level: SafetyLevel
    reasons: list[str] = []
    crisis_response: str | None = None


class SubscriptionValidationRequest(BaseModel):
    user_id: str
    platform: str
    receipt_or_purchase_token: str


class SubscriptionValidationResponse(BaseModel):
    user_id: str
    platform: str
    valid: bool
    entitlement: str
    message: str
