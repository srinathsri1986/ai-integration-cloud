"""SAP ERP connector plugin (mock mode)."""
from __future__ import annotations
from ..base import ConnectorTool, ConnectorToolParam

_TOOLS = [
    ConnectorTool("post_journal_entry", "Post Journal Entry", "Post a double-entry journal to the general ledger.", "sap",
                  [ConnectorToolParam("debit_account", "string", True, "GL debit account code"),
                   ConnectorToolParam("credit_account", "string", True, "GL credit account code"),
                   ConnectorToolParam("amount", "number", True, "Transaction amount"),
                   ConnectorToolParam("currency", "string", False, "ISO currency code"),
                   ConnectorToolParam("posting_date", "string", False, "Posting date YYYY-MM-DD")]),
    ConnectorTool("get_cost_center", "Get Cost Center", "Retrieve cost center details and YTD spend.", "sap",
                  [ConnectorToolParam("cost_center_id", "string", True, "SAP cost center ID")]),
    ConnectorTool("get_gl_balance", "Get G/L Balance", "Current balance for a G/L account.", "sap",
                  [ConnectorToolParam("account_code", "string", True, "G/L account code"),
                   ConnectorToolParam("fiscal_period", "string", False, "Fiscal period e.g. 2026-03")]),
    ConnectorTool("list_vendors", "List Vendors", "Paginated list of approved vendors.", "sap",
                  [ConnectorToolParam("limit", "number", False, "Max records")]),
    ConnectorTool("create_purchase_order", "Create Purchase Order", "Raise a purchase order for approval.", "sap",
                  [ConnectorToolParam("vendor_id", "string", True, "Vendor ID"),
                   ConnectorToolParam("line_items", "string", True, "JSON array of line items"),
                   ConnectorToolParam("currency", "string", False, "ISO currency code")]),
]
_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

_MOCK = {
    "post_journal_entry": {"documentNumber": "JE-20260315-001", "status": "posted"},
    "get_cost_center": {"id": "CC-1100", "name": "Engineering", "ytdSpend": 412000, "budget": 600000},
    "get_gl_balance": {"accountCode": "1000", "balance": 2450000, "currency": "USD"},
    "list_vendors": {"items": [{"id": "V-001", "name": "Tech Supplies Ltd"}, {"id": "V-002", "name": "Cloud Services Inc"}], "total": 2},
    "create_purchase_order": {"poNumber": "PO-2026-0099", "status": "pending_approval"},
}


class SAPPlugin:
    connector_id = "sap"
    name = "SAP ERP"
    logo_slug = "sap"
    auth_scheme = "basic"

    def list_tools(self): return list(_TOOLS)
    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP: raise KeyError(f"Unknown SAP tool: {tool_id!r}")
        return {"connector": "sap", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}
    def test_connection(self): return {"ok": True, "message": "SAP mock connector is ready (mock mode)."}
