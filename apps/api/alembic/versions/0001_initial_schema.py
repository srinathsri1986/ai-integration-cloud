"""Initial schema — Release 4.0 baseline.

This migration creates the full schema as it exists after Release 4.0,
including all columns that were previously added by the _ensure_* guards
in database.py.

To apply to an existing database that was already created via create_all():
    alembic stamp head

To apply to a fresh database:
    alembic upgrade head

Revision ID: 0001
Revises: (none)
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tenants ──────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("plan", sa.String(32), nullable=False, server_default="starter"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(64), nullable=False, server_default="Integration Admin"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_token", sa.String(255), nullable=True),
        sa.Column("reset_token", sa.String(255), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── tenant_members ───────────────────────────────────────────────────────
    op.create_table(
        "tenant_members",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_members_tenant_user", "tenant_members", ["tenant_id", "user_id"], unique=True
    )

    # ── tenant_invites ───────────────────────────────────────────────────────
    op.create_table(
        "tenant_invites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_tenant_invites_token", "tenant_invites", ["token"], unique=True)
    op.create_index(
        "ix_tenant_invites_email_tenant", "tenant_invites", ["email", "tenant_id"]
    )

    # ── audit_logs ───────────────────────────────────────────────────────────
    _jsonb = postgresql.JSONB(astext_type=sa.Text())
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("timestamp", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("user", sa.String(128), nullable=False),
        sa.Column("channel", sa.String(64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("detected_intent", sa.String(128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("tools_used", _jsonb, nullable=False),
        sa.Column("endpoint_called", sa.String(256), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.String(128), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("ai_provider", sa.String(64), nullable=False),
        sa.Column("ai_mode", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("model_call_attempted", sa.Boolean(), nullable=False),
        sa.Column("model_call_succeeded", sa.Boolean(), nullable=False),
        sa.Column("used_fallback_router", sa.Boolean(), nullable=False),
        sa.Column("narrative_provider", sa.String(64), nullable=False),
        sa.Column("narrative_model", sa.String(128), nullable=True),
        sa.Column("narrative_generated", sa.Boolean(), nullable=False),
        sa.Column("narrative_fallback_used", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", _jsonb, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index(
        "ix_audit_logs_detected_intent_created_at",
        "audit_logs",
        ["detected_intent", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_ai_provider_created_at", "audit_logs", ["ai_provider", "created_at"]
    )
    op.create_index(
        "ix_audit_logs_success_created_at", "audit_logs", ["success", "created_at"]
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])

    # ── flow_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "flow_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("flow_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.String(64), nullable=False),
        sa.Column("completed_at", sa.String(64), nullable=True),
        sa.Column("tools_used", _jsonb, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", _jsonb, nullable=False),
        sa.Column(
            "execution_timeline",
            _jsonb,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flow_runs_request_id", "flow_runs", ["request_id"])
    op.create_index(
        "ix_flow_runs_flow_id_started_at", "flow_runs", ["flow_id", "started_at"]
    )
    op.create_index(
        "ix_flow_runs_status_started_at", "flow_runs", ["status", "started_at"]
    )
    op.create_index("ix_flow_runs_tenant_id", "flow_runs", ["tenant_id"])

    # ── flow_definitions ─────────────────────────────────────────────────────
    op.create_table(
        "flow_definitions",
        sa.Column("flow_id", sa.String(96), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_connector", sa.String(64), nullable=False),
        sa.Column("target_module", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("mapping_definition_id", sa.String(96), nullable=True),
        sa.Column("trigger_cron", sa.String(100), nullable=True),
        sa.Column("webhook_secret", sa.String(64), nullable=True),
        sa.Column("last_run_at", sa.String(64), nullable=True),
        sa.Column("last_run_status", sa.String(32), nullable=False),
        sa.Column("steps", _jsonb, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("flow_id"),
    )
    op.create_index("ix_flow_definitions_status", "flow_definitions", ["status"])
    op.create_index(
        "ix_flow_definitions_target_module", "flow_definitions", ["target_module"]
    )
    op.create_index("ix_flow_definitions_tenant_id", "flow_definitions", ["tenant_id"])

    # ── mapping_definitions ───────────────────────────────────────────────────
    op.create_table(
        "mapping_definitions",
        sa.Column("mapping_id", sa.String(96), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_object_id", sa.String(80), nullable=False),
        sa.Column("target_object_id", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mappings", _jsonb, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("mapping_id"),
    )
    op.create_index("ix_mapping_definitions_status", "mapping_definitions", ["status"])
    op.create_index(
        "ix_mapping_definitions_source_target",
        "mapping_definitions",
        ["source_object_id", "target_object_id"],
    )
    op.create_index(
        "ix_mapping_definitions_tenant_id", "mapping_definitions", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_table("mapping_definitions")
    op.drop_table("flow_definitions")
    op.drop_table("flow_runs")
    op.drop_table("audit_logs")
    op.drop_table("tenant_invites")
    op.drop_table("tenant_members")
    op.drop_table("users")
    op.drop_table("tenants")
