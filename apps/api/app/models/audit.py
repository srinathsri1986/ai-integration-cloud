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


class AuditLogSummary(BaseModel):
    total: int
    successes: int
    failures: int
    fallback_count: int = Field(alias="fallbackCount")
    average_latency_ms: float = Field(alias="averageLatencyMs")
    by_intent: dict[str, int] = Field(alias="byIntent")
