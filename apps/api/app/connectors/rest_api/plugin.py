"""REST API connector plugin — template-based HTTP calls (mock mode).

No arbitrary endpoint execution. All URLs must be pre-registered as approved
templates before they can be called through this connector.
"""
from __future__ import annotations

from ..base import ConnectorTool, ConnectorToolParam

_TOOLS = [
    ConnectorTool(
        "http_get",
        "HTTP GET (Approved Template)",
        "Execute an approved GET request template. Template URL and headers are pre-configured; only path/query params may be supplied at runtime.",
        "rest-api",
        [
            ConnectorToolParam("template_id", "string", True, "Approved request template identifier"),
            ConnectorToolParam("path_params", "string", False, "JSON object of URL path parameters"),
            ConnectorToolParam("query_params", "string", False, "JSON object of query-string parameters"),
        ],
    ),
    ConnectorTool(
        "http_post",
        "HTTP POST (Approved Template)",
        "Execute an approved POST request template. Template URL and auth are pre-configured; only the approved body schema may be populated at runtime.",
        "rest-api",
        [
            ConnectorToolParam("template_id", "string", True, "Approved request template identifier"),
            ConnectorToolParam("body", "string", False, "JSON body (must conform to the template's approved schema)"),
        ],
    ),
]

_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

_MOCK = {
    "http_get": {
        "templateId": "product_catalog_list",
        "url": "https://api.example.com/products",
        "status": 200,
        "body": {"items": [{"id": "P-001", "name": "Widget Pro", "price": 49.99}], "total": 1},
        "latencyMs": 82,
    },
    "http_post": {
        "templateId": "create_order",
        "url": "https://api.example.com/orders",
        "status": 201,
        "body": {"orderId": "ORD-2026-0042", "status": "created", "message": "Order accepted."},
        "latencyMs": 134,
    },
}


class RESTAPIPlugin:
    connector_id = "rest-api"
    name = "REST API"
    logo_slug = "rest-api"
    auth_scheme = "api_key"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown REST API tool: {tool_id!r}")
        return {"connector": "rest-api", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}

    def test_connection(self) -> dict:
        return {"ok": True, "message": "REST API mock connector is ready (mock mode). Register approved templates to use in production."}
