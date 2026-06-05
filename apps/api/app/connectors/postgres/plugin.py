"""PostgreSQL connector plugin — approved parameterised query templates (mock mode)."""
from __future__ import annotations
from ..base import ConnectorTool, ConnectorToolParam

_TOOLS = [
    ConnectorTool("run_approved_query", "Run Approved Query", "Execute a pre-approved parameterised query template. No raw SQL.", "postgres",
                  [ConnectorToolParam("template_id", "string", True, "Approved query template identifier"),
                   ConnectorToolParam("params", "string", False, "JSON object of bind parameters")]),
    ConnectorTool("list_approved_templates", "List Approved Templates", "List all query templates approved for execution.", "postgres"),
    ConnectorTool("describe_table", "Describe Table", "Return column schema for an approved table.", "postgres",
                  [ConnectorToolParam("table_name", "string", True, "Approved table name")]),
]
_TOOL_MAP = {t.tool_id: t for t in _TOOLS}
_MOCK = {
    "run_approved_query": {"templateId": "revenue_by_month", "rows": [{"month": "2026-01", "revenue": 820000}, {"month": "2026-02", "revenue": 910000}], "rowCount": 2},
    "list_approved_templates": {"templates": [{"id": "revenue_by_month", "description": "Monthly revenue rollup"}, {"id": "customer_churn", "description": "Churned customers in period"}]},
    "describe_table": {"table": "orders", "columns": [{"name": "id", "type": "uuid"}, {"name": "total_amount", "type": "numeric"}, {"name": "created_at", "type": "timestamptz"}]},
}


class PostgreSQLPlugin:
    connector_id = "postgres"
    name = "PostgreSQL"
    logo_slug = "postgres"
    auth_scheme = "basic"

    def list_tools(self): return list(_TOOLS)
    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP: raise KeyError(f"Unknown PostgreSQL tool: {tool_id!r}")
        return {"connector": "postgres", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}
    def test_connection(self): return {"ok": True, "message": "PostgreSQL mock connector is ready (mock mode)."}
