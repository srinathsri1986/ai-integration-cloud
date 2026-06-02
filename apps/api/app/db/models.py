from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _json_type() -> JSON:
    return JSON().with_variant(JSONB(), "postgresql")


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_request_id", "request_id"),
        Index("ix_audit_logs_detected_intent_created_at", "detected_intent", "created_at"),
        Index("ix_audit_logs_ai_provider_created_at", "ai_provider", "created_at"),
        Index("ix_audit_logs_success_created_at", "success", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    flow_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[str] = mapped_column(String(64), nullable=False)
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
    )

    flow_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_connector: Mapped[str] = mapped_column(String(64), nullable=False)
    target_module: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_definition_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    last_run_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_run_status: Mapped[str] = mapped_column(String(32), nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(_json_type(), nullable=False)
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
    )

    mapping_id: Mapped[str] = mapped_column(String(96), primary_key=True)
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
