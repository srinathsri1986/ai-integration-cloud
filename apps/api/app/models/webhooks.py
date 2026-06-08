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
    # CloudEvents envelope attributes (Release 20.0) — populated only when the
    # inbound payload was detected as a CloudEvent (binary or structured content
    # mode), e.g. events from an SAP BTP Event Mesh broker. Null otherwise.
    event_id: str | None = Field(default=None, alias="eventId")
    event_source: str | None = Field(default=None, alias="eventSource")
    event_type: str | None = Field(default=None, alias="eventType")
    event_spec_version: str | None = Field(default=None, alias="eventSpecVersion")


class WebhookDeliveryStats(BaseModel):
    """Aggregate stats for the webhook delivery dashboard."""

    total: int
    succeeded: int
    failed: int
    dead_letter: int = Field(alias="deadLetter")
    processing: int
