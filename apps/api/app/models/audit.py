from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    timestamp: str
    request_id: str = Field(alias="requestId")
    user: str
    channel: str
    question: str
    detected_intent: str = Field(alias="detectedIntent")
    confidence: float = Field(ge=0, le=1)
    tools_used: list[str] = Field(alias="toolsUsed")
    endpoint_called: str = Field(alias="endpointCalled")
    fallback_used: bool = Field(alias="fallbackUsed")
    success: bool
    failure_reason: str | None = Field(default=None, alias="failureReason")
    latency_ms: int = Field(alias="latencyMs")
    ai_provider: str = Field(default="none", alias="aiProvider")
    ai_mode: str = Field(default="disabled", alias="aiMode")
    model_name: str | None = Field(default=None, alias="modelName")
    model_call_attempted: bool = Field(default=False, alias="modelCallAttempted")
    model_call_succeeded: bool = Field(default=False, alias="modelCallSucceeded")
    used_fallback_router: bool = Field(default=False, alias="usedFallbackRouter")


class AuditLogSummary(BaseModel):
    total: int
    successes: int
    failures: int
    fallback_count: int = Field(alias="fallbackCount")
    average_latency_ms: float = Field(alias="averageLatencyMs")
    by_intent: dict[str, int] = Field(alias="byIntent")
