"""PostgreSQL connector plugin — approved parameterised query templates (mock + live mode).

In mock mode: returns structured fake responses.
In live mode (connection string stored via /connectors/postgres/live-config):
    uses psycopg (v3, already in deps) to execute pre-approved parameterised query templates.

Security:
- No arbitrary SQL execution.
- All queries are pre-approved named templates defined in _QUERY_TEMPLATES below.
- Runtime callers supply only the template_id and a dict of bind parameters.
- The connection string is encrypted at rest via ConnectorCredentialService.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from ..base import ConnectorTool, ConnectorToolParam

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Approved query templates — no runtime SQL injection possible
# ---------------------------------------------------------------------------

_QUERY_TEMPLATES: dict[str, dict[str, Any]] = {
    "revenue_by_month": {
        "sql": "SELECT date_trunc('month', created_at) AS month, SUM(amount) AS revenue FROM orders WHERE created_at >= %(since)s GROUP BY 1 ORDER BY 1 DESC LIMIT %(limit)s",
        "params": {"since": "2025-01-01", "limit": 12},
        "description": "Monthly revenue rollup from orders table.",
    },
    "customer_churn": {
        "sql": "SELECT customer_id, last_order_at, CURRENT_DATE - last_order_at::date AS days_since FROM customers WHERE last_order_at < CURRENT_DATE - INTERVAL '%(days)s days' ORDER BY days_since DESC LIMIT %(limit)s",
        "params": {"days": 90, "limit": 50},
        "description": "Customers who have not ordered in N days.",
    },
    "top_products": {
        "sql": "SELECT product_id, product_name, SUM(quantity) AS units_sold FROM order_items GROUP BY 1, 2 ORDER BY 3 DESC LIMIT %(limit)s",
        "params": {"limit": 10},
        "description": "Top selling products by units sold.",
    },
    "active_users": {
        "sql": "SELECT COUNT(*) AS active_users FROM users WHERE last_login_at >= CURRENT_DATE - INTERVAL '%(days)s days'",
        "params": {"days": 30},
        "description": "Count of users active in the last N days.",
    },
}

_TOOLS = [
    ConnectorTool(
        "run_approved_query",
        "Run Approved Query",
        "Execute a pre-approved parameterised query template. No raw SQL.",
        "postgres",
        [
            ConnectorToolParam("template_id", "string", True, "Approved query template identifier"),
            ConnectorToolParam("params", "string", False, "JSON object of bind parameters (merged with template defaults)"),
        ],
    ),
    ConnectorTool(
        "list_approved_templates",
        "List Approved Templates",
        "Return all query templates approved for execution.",
        "postgres",
    ),
    ConnectorTool(
        "describe_table",
        "Describe Table",
        "Return column schema for an approved table.",
        "postgres",
        [ConnectorToolParam("table_name", "string", True, "Approved table name (orders, customers, products, order_items, users)")],
    ),
]

_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

# Tables that may be described (allowlist — no arbitrary information_schema queries)
_ALLOWED_TABLES = {"orders", "customers", "products", "order_items", "users"}

_MOCK = {
    "run_approved_query": {
        "templateId": "revenue_by_month",
        "rows": [
            {"month": "2026-01-01", "revenue": 820000},
            {"month": "2026-02-01", "revenue": 910000},
        ],
        "rowCount": 2,
    },
    "list_approved_templates": {
        "templates": [
            {"id": k, "description": v["description"], "defaultParams": v["params"]}
            for k, v in _QUERY_TEMPLATES.items()
        ]
    },
    "describe_table": {
        "table": "orders",
        "columns": [
            {"name": "id", "type": "uuid"},
            {"name": "customer_id", "type": "uuid"},
            {"name": "amount", "type": "numeric"},
            {"name": "created_at", "type": "timestamptz"},
        ],
    },
}


def _get_live_creds(tenant_id: int | None = None) -> dict | None:
    try:
        from app.services.credential_service import credential_service
        return credential_service.get_credentials("postgres", tenant_id)
    except Exception as exc:
        logger.debug("Could not load PostgreSQL credentials: %s", exc)
    return None


def _execute_live(tool_id: str, params: dict, creds: dict) -> dict:
    """Execute an approved template against the configured PostgreSQL database."""
    import psycopg  # psycopg v3 — already in pyproject.toml as psycopg[binary]

    conn_str = creds.get("connection_string", "")
    if not conn_str:
        raise RuntimeError("PostgreSQL connector: connection_string is not configured.")

    if tool_id == "list_approved_templates":
        return {
            "connector": "postgres",
            "tool": tool_id,
            "mode": "live",
            "result": {
                "templates": [
                    {"id": k, "description": v["description"], "defaultParams": v["params"]}
                    for k, v in _QUERY_TEMPLATES.items()
                ]
            },
        }

    with psycopg.connect(conn_str) as conn:
        if tool_id == "describe_table":
            table_name = params.get("table_name", "")
            if table_name not in _ALLOWED_TABLES:
                raise ValueError(
                    f"Table '{table_name}' is not on the approved list. "
                    f"Allowed: {sorted(_ALLOWED_TABLES)}"
                )
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = %s ORDER BY ordinal_position",
                    (table_name,),
                )
                cols = [{"name": row[0], "type": row[1]} for row in cur.fetchall()]
            return {
                "connector": "postgres",
                "tool": tool_id,
                "mode": "live",
                "result": {"table": table_name, "columns": cols},
            }

        elif tool_id == "run_approved_query":
            template_id = params.get("template_id", "")
            template = _QUERY_TEMPLATES.get(template_id)
            if not template:
                raise ValueError(
                    f"Unknown template '{template_id}'. "
                    f"Allowed: {list(_QUERY_TEMPLATES)}"
                )

            # Merge caller params over template defaults
            raw_params = params.get("params") or "{}"
            caller_params = json.loads(raw_params) if isinstance(raw_params, str) else raw_params
            bind = {**template["params"], **caller_params}

            with conn.cursor() as cur:
                cur.execute(template["sql"], bind)
                col_names = [desc.name for desc in (cur.description or [])]
                rows = [dict(zip(col_names, row)) for row in cur.fetchall()]

            return {
                "connector": "postgres",
                "tool": tool_id,
                "mode": "live",
                "result": {"templateId": template_id, "rows": rows, "rowCount": len(rows)},
            }

    raise KeyError(f"Unknown PostgreSQL tool: {tool_id!r}")


class PostgreSQLPlugin:
    connector_id = "postgres"
    name = "PostgreSQL"
    logo_slug = "postgres"
    auth_scheme = "basic"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown PostgreSQL tool: {tool_id!r}")

        tenant_id: int | None = params.get("tenant_id")
        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                return _execute_live(tool_id, params, creds)
            except Exception as exc:
                logger.warning(
                    "PostgreSQL live execution failed for tool=%s, falling back to mock: %s",
                    tool_id,
                    exc,
                )

        return {"connector": "postgres", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}

    def test_connection(self) -> dict:
        creds = _get_live_creds()
        if creds:
            conn_str = creds.get("connection_string", "")
            try:
                import psycopg
                with psycopg.connect(conn_str, connect_timeout=5) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT version()")
                        version = (cur.fetchone() or [""])[0]
                return {
                    "ok": True,
                    "mode": "live",
                    "message": f"Connected to PostgreSQL. {version[:60]}",
                }
            except Exception as exc:
                return {
                    "ok": False,
                    "mode": "live",
                    "message": f"PostgreSQL connection failed: {exc}",
                }

        return {
            "ok": True,
            "mode": "mock",
            "message": "PostgreSQL connector ready in mock mode. Click Configure to add a connection string.",
        }
