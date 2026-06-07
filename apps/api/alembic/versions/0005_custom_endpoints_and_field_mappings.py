"""Add custom_endpoints table and inline field_mappings on flows — R18a.

Two additions:

1.  custom_endpoints — lets users register any REST API as a source or target
    connector without needing a pre-built plugin.  Credentials are stored
    encrypted via credential_service; field_schema holds the discovered layout.

2.  flow_definitions.field_mappings (JSONB) — inline field mapping rows that
    live directly on a flow definition.  This is distinct from the
    mapping_definition_id / MappingDefinition lifecycle which gates
    compliance-controlled catalog integrations.  User-wizard mappings are
    stored here so they travel with the flow and are versioned with it.

3.  flow_definitions.target_connector (TEXT) — explicit target connector ID.
    Previously stored in target_module (a misnomer).  Both columns are kept;
    target_connector is preferred for new flows.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── custom_endpoints ──────────────────────────────────────────────────────
    op.create_table(
        "custom_endpoints",
        sa.Column("id",              sa.Text,    primary_key=True),
        sa.Column("tenant_id",       sa.Integer, nullable=True),
        sa.Column("name",            sa.Text,    nullable=False),
        sa.Column("description",     sa.Text,    nullable=False, server_default=""),
        sa.Column("base_url",        sa.Text,    nullable=False),
        sa.Column("auth_scheme",     sa.Text,    nullable=False, server_default="none"),
        # Stored as e.g. "api_key:Authorization" or "bearer:Authorization"
        sa.Column("auth_header_name", sa.Text,   nullable=True),
        sa.Column("default_path",    sa.Text,    nullable=False, server_default="/"),
        sa.Column("http_method",     sa.Text,    nullable=False, server_default="GET"),
        # Discovered or manually defined field list — list[FieldInfo] JSON
        sa.Column("field_schema",    sa.Text,    nullable=False, server_default="[]"),
        # Last raw sample response (for re-discovery UX only — never used in exec)
        sa.Column("sample_response", sa.Text,    nullable=True),
        sa.Column("created_at",      sa.Text,    nullable=False),
        sa.Column("updated_at",      sa.Text,    nullable=False),
    )
    op.create_index("ix_custom_endpoints_tenant", "custom_endpoints", ["tenant_id"])

    # ── flow_definitions: new columns ─────────────────────────────────────────
    with op.batch_alter_table("flow_definitions") as batch_op:
        batch_op.add_column(
            sa.Column("target_connector", sa.Text, nullable=True)
        )
        batch_op.add_column(
            sa.Column("field_mappings", sa.Text, nullable=False, server_default="[]")
        )


def downgrade() -> None:
    with op.batch_alter_table("flow_definitions") as batch_op:
        batch_op.drop_column("field_mappings")
        batch_op.drop_column("target_connector")
    op.drop_index("ix_custom_endpoints_tenant", table_name="custom_endpoints")
    op.drop_table("custom_endpoints")
