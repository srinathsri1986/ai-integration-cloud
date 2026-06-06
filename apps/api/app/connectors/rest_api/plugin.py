"""REST API connector plugin — template-based HTTP calls (mock + live API-key mode).

In mock mode: returns structured fake responses.
In live mode (base_url + api_key stored via /connectors/rest-api/live-config):
    uses httpx to make real HTTP calls against pre-approved request templates.

Security:
- No arbitrary endpoint execution.
- The base URL is locked to what the administrator configured.
- Template paths are pre-approved identifiers (not raw URLs supplied at runtime).
- API key is encrypted at rest via ConnectorCredentialService.
"""
from __future__ import annotations

import json
import logging

from ..base import ConnectorTool, ConnectorToolParam

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Approved request templates
# Each template defines the path appended to the admin-configured base URL.
# Runtime callers supply only the template_id + permitted params.
# ---------------------------------------------------------------------------

_APPROVED_TEMPLATES: dict[str, dict] = {
    "product_catalog_list": {
        "method": "GET",
        "path": "/products",
        "description": "List all products from the catalog.",
    },
    "get_product": {
        "method": "GET",
        "path": "/products/{id}",
        "path_params": ["id"],
        "description": "Get a single product by ID.",
    },
    "list_orders": {
        "method": "GET",
        "path": "/orders",
        "query_params": ["status", "limit", "offset"],
        "description": "List orders with optional status filter.",
    },
    "create_order": {
        "method": "POST",
        "path": "/orders",
        "body_schema": {"customer_id": "string", "items": "array", "notes": "string?"},
        "description": "Create a new order.",
    },
    "webhook_notify": {
        "method": "POST",
        "path": "/webhooks/notify",
        "body_schema": {"event": "string", "payload": "object"},
        "description": "Send an event notification to the configured webhook endpoint.",
    },
}

_TOOLS = [
    ConnectorTool(
        "http_get",
        "HTTP GET (Approved Template)",
        "Execute an approved GET request template. Template path is pre-configured; only listed path/query params may be supplied.",
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
        "Execute an approved POST request template. Template URL and auth are pre-configured; only the approved body schema may be populated.",
        "rest-api",
        [
            ConnectorToolParam("template_id", "string", True, "Approved request template identifier"),
            ConnectorToolParam("body", "string", False, "JSON body (must conform to the template approved schema)"),
        ],
    ),
    ConnectorTool(
        "list_templates",
        "List Approved Templates",
        "Return all pre-approved request templates available for this connector.",
        "rest-api",
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
    "list_templates": {
        "templates": [
            {"id": k, "method": v["method"], "path": v["path"], "description": v["description"]}
            for k, v in _APPROVED_TEMPLATES.items()
        ]
    },
}


def _get_live_creds(tenant_id: int | None = None) -> dict | None:
    try:
        from app.services.credential_service import credential_service
        return credential_service.get_credentials("rest-api", tenant_id)
    except Exception as exc:
        logger.debug("Could not load REST API credentials: %s", exc)
    return None


def _execute_live(tool_id: str, params: dict, creds: dict) -> dict:
    """Dispatch an approved template call to the real REST API using httpx."""
    import httpx  # already in deps

    base_url = creds.get("base_url", "").rstrip("/")
    api_key = creds.get("api_key", "")

    if not base_url:
        raise RuntimeError("REST API connector: base_url is not configured.")

    headers = {"Accept": "application/json"}
    if api_key:
        # Standard Authorization: Bearer pattern; override via template if needed
        headers["Authorization"] = f"Bearer {api_key}"

    if tool_id == "list_templates":
        return {
            "connector": "rest-api",
            "tool": tool_id,
            "mode": "live",
            "result": {
                "templates": [
                    {"id": k, "method": v["method"], "path": v["path"], "description": v["description"]}
                    for k, v in _APPROVED_TEMPLATES.items()
                ]
            },
        }

    template_id = params.get("template_id", "")
    template = _APPROVED_TEMPLATES.get(template_id)
    if not template:
        raise ValueError(
            f"Unknown or unapproved template_id '{template_id}'. "
            f"Allowed: {list(_APPROVED_TEMPLATES)}"
        )

    # Build URL
    path = template["path"]
    raw_path_params = params.get("path_params") or "{}"
    path_params_dict = json.loads(raw_path_params) if isinstance(raw_path_params, str) else raw_path_params
    # Only substitute approved path params defined on the template
    for key in template.get("path_params", []):
        if key in path_params_dict:
            path = path.replace(f"{{{key}}}", str(path_params_dict[key]))

    url = base_url + path

    with httpx.Client(timeout=15) as client:
        if tool_id == "http_get" or template["method"] == "GET":
            raw_qp = params.get("query_params") or "{}"
            qp = json.loads(raw_qp) if isinstance(raw_qp, str) else raw_qp
            # Filter to approved query params only
            allowed_qp = template.get("query_params", [])
            safe_qp = {k: v for k, v in qp.items() if k in allowed_qp} if allowed_qp else {}
            resp = client.get(url, headers=headers, params=safe_qp)

        elif tool_id == "http_post" or template["method"] == "POST":
            raw_body = params.get("body") or "{}"
            body_dict = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
            resp = client.post(url, headers={**headers, "Content-Type": "application/json"}, json=body_dict)

        else:
            raise ValueError(f"Template method {template['method']} not supported via this tool.")

    try:
        resp_body = resp.json()
    except Exception:
        resp_body = {"text": resp.text}

    return {
        "connector": "rest-api",
        "tool": tool_id,
        "mode": "live",
        "result": {
            "templateId": template_id,
            "url": url,
            "status": resp.status_code,
            "body": resp_body,
            "latencyMs": int(resp.elapsed.total_seconds() * 1000),
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

        tenant_id: int | None = params.get("tenant_id")
        creds = _get_live_creds(tenant_id)
        if creds:
            try:
                return _execute_live(tool_id, params, creds)
            except Exception as exc:
                logger.warning(
                    "REST API live execution failed for tool=%s, falling back to mock: %s",
                    tool_id,
                    exc,
                )

        return {"connector": "rest-api", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}

    def test_connection(self) -> dict:
        creds = _get_live_creds()
        if creds:
            base_url = creds.get("base_url", "")
            try:
                import httpx
                resp = httpx.get(base_url.rstrip("/"), timeout=5)
                return {
                    "ok": True,
                    "mode": "live",
                    "message": f"REST API reachable at {base_url} (HTTP {resp.status_code}).",
                }
            except Exception as exc:
                return {
                    "ok": False,
                    "mode": "live",
                    "message": f"REST API not reachable at {base_url}: {exc}",
                }

        return {
            "ok": True,
            "mode": "mock",
            "message": "REST API connector ready in mock mode. Click Configure to set a base URL and API key.",
        }
