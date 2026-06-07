"""Add composite indexes for multi-tenant scale — R17.

High-volume SaaS query patterns that become slow without these indexes:

1. Dashboard: "latest N runs for tenant T"
   → flow_runs(tenant_id, started_at DESC)

2. Per-flow history panel: "runs for tenant T on flow F, newest first"
   → flow_runs(tenant_id, flow_id, started_at DESC)

3. Governance console: "audit entries for tenant T, newest first"
   → audit_log_entries(tenant_id, timestamp DESC)

4. Integration status list filtered by status:
   → flow_definitions(tenant_id, status)

5. Connector config per-tenant lookup:
   → connector_config_records(tenant_id, connector_id) — already unique-indexed,
     but adding explicit index for fast full-tenant scans.

At scale (millions of rows), the existing single-column indexes can still cause
full-table scans when combined with ORDER BY.  These composite indexes let
Postgres satisfy the WHERE + ORDER BY in a single index scan.

NOTE: For very large deployments (10M+ rows per tenant), consider declarative
table partitioning on tenant_id.  This migration is the foundation — partitioning
can be layered on top without changing application queries.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-07
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── flow_runs ─────────────────────────────────────────────────────────────
    # Dashboard query: SELECT * FROM flow_runs WHERE tenant_id = ? ORDER BY started_at DESC LIMIT 50
    op.create_index(
        "ix_flow_runs_tenant_started_at",
        "flow_runs",
        ["tenant_id", "started_at"],
        if_not_exists=True,
    )
    # Per-flow history: SELECT * FROM flow_runs WHERE tenant_id = ? AND flow_id = ? ORDER BY started_at DESC
    op.create_index(
        "ix_flow_runs_tenant_flow_started",
        "flow_runs",
        ["tenant_id", "flow_id", "started_at"],
        if_not_exists=True,
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    # Governance console: SELECT * FROM audit_logs WHERE tenant_id = ? ORDER BY timestamp DESC LIMIT 100
    op.create_index(
        "ix_audit_logs_tenant_timestamp",
        "audit_logs",
        ["tenant_id", "timestamp"],
        if_not_exists=True,
    )

    # ── flow_definitions ──────────────────────────────────────────────────────
    # Integration status list filtered by status (e.g. WHERE tenant_id = ? AND status = 'published')
    op.create_index(
        "ix_flow_definitions_tenant_status",
        "flow_definitions",
        ["tenant_id", "status"],
        if_not_exists=True,
    )

    # ── connector_config_records ──────────────────────────────────────────────
    # Fast tenant-scoped connector list (GET /connectors)
    op.create_index(
        "ix_connector_config_tenant",
        "connector_config_records",
        ["tenant_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_connector_config_tenant",       table_name="connector_config_records")
    op.drop_index("ix_flow_definitions_tenant_status", table_name="flow_definitions")
    op.drop_index("ix_audit_logs_tenant_timestamp", table_name="audit_logs")
    op.drop_index("ix_flow_runs_tenant_flow_started",  table_name="flow_runs")
    op.drop_index("ix_flow_runs_tenant_started_at",    table_name="flow_runs")
