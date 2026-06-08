"""Add CloudEvents attribute columns to webhook_deliveries — Release 20.0.

Surfaces the CNCF CloudEvents envelope's core attributes (id, source, type,
specversion) on each delivery record when the inbound payload is detected as
a CloudEvent (binary or structured content mode) — e.g. events emitted by an
SAP BTP Event Mesh broker. All columns are nullable: deliveries that are not
CloudEvents simply leave them null, so this is fully backward compatible with
existing R12 webhook traffic.

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("webhook_deliveries", sa.Column("event_id", sa.String(128), nullable=True))
    op.add_column("webhook_deliveries", sa.Column("event_source", sa.String(256), nullable=True))
    op.add_column("webhook_deliveries", sa.Column("event_type", sa.String(256), nullable=True))
    op.add_column("webhook_deliveries", sa.Column("event_spec_version", sa.String(16), nullable=True))
    op.create_index(
        "ix_webhook_deliveries_event_type",
        "webhook_deliveries",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliveries_event_type", table_name="webhook_deliveries")
    op.drop_column("webhook_deliveries", "event_spec_version")
    op.drop_column("webhook_deliveries", "event_type")
    op.drop_column("webhook_deliveries", "event_source")
    op.drop_column("webhook_deliveries", "event_id")
