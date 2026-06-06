"""Add webhook_deliveries table — Release 12.0 webhook hardening.

Tracks every inbound webhook delivery: status, attempt count, payload hash,
linked flow-run request_id, and dead-letter flag.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("delivery_id", sa.String(64), nullable=False, unique=True),
        sa.Column("flow_id", sa.String(128), nullable=False),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        # SHA-256 hex of raw request body — audit trail without storing the payload
        sa.Column("payload_hash", sa.String(64), nullable=False),
        # pending | processing | succeeded | failed | dead_letter
        sa.Column("status", sa.String(32), nullable=False, server_default="processing"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("received_at", sa.String(64), nullable=False),
        sa.Column("next_retry_at", sa.String(64), nullable=True),
        sa.Column("completed_at", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_delivery_id",
        "webhook_deliveries",
        ["delivery_id"],
        unique=True,
    )
    op.create_index(
        "ix_webhook_deliveries_flow_id_received_at",
        "webhook_deliveries",
        ["flow_id", "received_at"],
    )
    op.create_index(
        "ix_webhook_deliveries_status",
        "webhook_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_webhook_deliveries_tenant_id",
        "webhook_deliveries",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_tenant_id", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_status", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_flow_id_received_at", table_name="webhook_deliveries")
    op.drop_index("ix_webhook_deliveries_delivery_id", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
