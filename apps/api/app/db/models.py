from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TenantRecord(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="starter")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class TenantMemberRecord(Base):
    __tablename__ = "tenant_members"
    __table_args__ = (
        Index("ix_tenant_members_tenant_user", "tenant_id", "user_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class TenantInviteRecord(Base):
    __tablename__ = "tenant_invites"
    __table_args__ = (
        Index("ix_tenant_invites_token", "token", unique=True),
        Index("ix_tenant_invites_email_tenant", "email", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class UserRecord(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="Integration Admin")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


def _json_type() -> JSON:
    return JSON().with_variant(JSONB(), "postgresql")


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_detected_intent_created_at", "detected_intent", "created_at"),
        Index("ix_audit_logs_ai_provider_created_at", "ai_provider", "created_at"),
        Index("ix_audit_logs_success_created_at", "success", "created_at"),
        Index("ix_audit_logs_tenant_id", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    detected_intent: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    tools_used: Mapped[list[str]] = mapped_column(_json_type(), nullable=False)
    endpoint_called: Mapped[str] = mapped_column(String(256), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_call_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    model_call_succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    used_fallback_router: Mapped[bool] = mapped_column(Boolean, nullable=False)
    narrative_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    narrative_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    narrative_generated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    narrative_fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)


class FlowRunRecord(Base):
    __tablename__ = "flow_runs"
    __table_args__ = (
        Index("ix_flow_runs_request_id", "request_id"),
        Index("ix_flow_runs_flow_id_started_at", "flow_id", "started_at"),
        Index("ix_flow_runs_status_started_at", "status", "started_at"),
        Index("ix_flow_runs_tenant_id", "tenant_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    flow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tools_used: Mapped[list[str]] = mapped_column(_json_type(), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)
    execution_timeline: Mapped[list[dict[str, Any]]] = mapped_column(_json_type(), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )


class FlowDefinitionRecord(Base):
    __tablename__ = "flow_definitions"
    __table_args__ = (
        Index("ix_flow_definitions_status", "status"),
        Index("ix_flow_definitions_target_module", "target_module"),
        Index("ix_flow_definitions_tenant_id", "tenant_id"),
    )

    flow_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_connector: Mapped[str] = mapped_column(String(64), nullable=False)
    target_module: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_definition_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    trigger_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_status: Mapped[str] = mapped_column(String(32), nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(_json_type(), nullable=False)
    # R18a: explicit target connector ID and inline user-defined field mappings
    target_connector: Mapped[str | None] = mapped_column(String(96), nullable=True)
    field_mappings: Mapped[list[dict[str, Any]]] = mapped_column(
        _json_type(), nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class CustomEndpointRecord(Base):
    """User-defined REST API endpoint used as source or target in a flow — R18a."""

    __tablename__ = "custom_endpoints"
    __table_args__ = (
        Index("ix_custom_endpoints_tenant", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    auth_scheme: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    auth_header_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_path: Mapped[str] = mapped_column(String(256), nullable=False, default="/")
    http_method: Mapped[str] = mapped_column(String(8), nullable=False, default="GET")
    # Stored as JSON text — list[FieldInfo]
    field_schema: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sample_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)


class WebhookDeliveryRecord(Base):
    """Tracks every inbound webhook delivery attempt — status, retries, dead-letters."""

    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_flow_id_received_at", "flow_id", "received_at"),
        Index("ix_webhook_deliveries_status", "status"),
        Index("ix_webhook_deliveries_tenant_id", "tenant_id"),
        Index("ix_webhook_deliveries_delivery_id", "delivery_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delivery_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    flow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    received_at: Mapped[str] = mapped_column(String(64), nullable=False)
    # SHA-256 hex digest of the raw body — audit trail without storing the payload itself
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # pending | processing | succeeded | failed | dead_letter
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # request_id of the resulting flow run (populated on success or first attempt)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_retry_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class MappingDefinitionRecord(Base):
    __tablename__ = "mapping_definitions"
    __table_args__ = (
        Index("ix_mapping_definitions_status", "status"),
        Index("ix_mapping_definitions_source_target", "source_object_id", "target_object_id"),
        Index("ix_mapping_definitions_tenant_id", "tenant_id"),
    )

    mapping_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_object_id: Mapped[str] = mapped_column(String(80), nullable=False)
    target_object_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    mappings: Mapped[list[dict[str, Any]]] = mapped_column(_json_type(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ConnectorConfigRecord(Base):
    """Per-tenant connector config. Encrypted OAuth tokens stored in config_json.

    Production path: store the Fernet key in AWS KMS and move token references
    to AWS Secrets Manager. The service interface is identical.
    """

    __tablename__ = "connector_config_records"
    __table_args__ = (
        Index("uq_connector_config_connector_tenant", "connector_id", "tenant_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    mode: Mapped[str] = mapped_column(Text, nullable=False, default="mock")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
