"""Pydantic models for webhook delivery tracking — Release 12.0."""
from __future__ import annotations

from pydantic import BaseModel, Field


class WebhookDelivery(BaseModel):
    """Single webhook delivery record."""

    delivery_id: str = Field(alias="deliveryId")
    flow_id: str = Field(alias="flowId")
    received_at: str = Field(alias="receivedAt")
    payload_hash: str = Field(alias="payloadHash")
    status: str                          # processing | succeeded | failed | dead_letter
    attempt_count: int = Field(alias="attemptCount")
    max_attempts: int = Field(alias="maxAttempts")
    last_error: str | None = Field(default=None, alias="lastError")
    request_id: str | None = Field(default=None, alias="requestId")
    next_retry_at: str | None = Field(default=None, alias="nextRetryAt")
    completed_at: str | None = Field(default=None, alias="completedAt")


class WebhookDeliveryStats(BaseModel):
    """Aggregate stats for the webhook delivery dashboard."""

    total: int
    succeeded: int
    failed: int
    dead_letter: int = Field(alias="deadLetter")
    processing: int
