"""Add connector_config_records table — Release 6.0.

Stores per-tenant connector configuration (credentials metadata, mode, status).
Real credential values are NEVER stored here; only references/metadata and mode flags.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "connector_config_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("connector_id", sa.Text, nullable=False),
        sa.Column("tenant_id", sa.Integer, nullable=True),
        # config_json stores non-secret metadata only (base URLs, account IDs, feature flags).
        # Secrets (API keys, OAuth tokens) must be stored in a secrets manager, not here.
        sa.Column("config_json", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.Text, nullable=False, server_default="not_configured"),
        sa.Column("mode", sa.Text, nullable=False, server_default="mock"),
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
    # Unique: one config record per (connector_id, tenant). NULL tenant_id = global default.
    op.create_index(
        "uq_connector_config_connector_tenant",
        "connector_config_records",
        ["connector_id", "tenant_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_connector_config_connector_tenant", table_name="connector_config_records")
    op.drop_table("connector_config_records")
