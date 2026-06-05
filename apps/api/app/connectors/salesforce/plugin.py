"""Salesforce CRM connector plugin (mock mode)."""
from __future__ import annotations
from ..base import ConnectorTool, ConnectorToolParam

_TOOLS = [
    ConnectorTool("create_opportunity", "Create Opportunity", "Create a new sales opportunity record.", "salesforce",
                  [ConnectorToolParam("name", "string", True, "Opportunity name"),
                   ConnectorToolParam("account_id", "string", False, "Parent account ID"),
                   ConnectorToolParam("amount", "number", False, "Expected revenue amount"),
                   ConnectorToolParam("close_date", "string", False, "Expected close date (YYYY-MM-DD)")]),
    ConnectorTool("update_contact", "Update Contact", "Update fields on an existing contact.", "salesforce",
                  [ConnectorToolParam("contact_id", "string", True, "Salesforce contact ID"),
                   ConnectorToolParam("email", "string", False, "New email address"),
                   ConnectorToolParam("title", "string", False, "Job title")]),
    ConnectorTool("get_account", "Get Account", "Retrieve account details by ID.", "salesforce",
                  [ConnectorToolParam("account_id", "string", True, "Salesforce account ID")]),
    ConnectorTool("list_opportunities", "List Opportunities", "List open opportunities, optionally filtered.", "salesforce",
                  [ConnectorToolParam("stage", "string", False, "Pipeline stage filter"),
                   ConnectorToolParam("limit", "number", False, "Max records to return")]),
    ConnectorTool("create_case", "Create Case", "Open a support case linked to an account.", "salesforce",
                  [ConnectorToolParam("account_id", "string", True, "Account ID"),
                   ConnectorToolParam("subject", "string", True, "Case subject"),
                   ConnectorToolParam("priority", "string", False, "High | Medium | Low")]),
]
_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

_MOCK_DATA = {
    "create_opportunity": {"id": "OPP-0042", "status": "created", "name": "Mock Opportunity"},
    "update_contact": {"id": "CON-0099", "status": "updated"},
    "get_account": {"id": "ACC-0001", "name": "Acme Corp", "industry": "Technology", "annualRevenue": 5000000},
    "list_opportunities": {"items": [{"id": "OPP-0040", "name": "Q4 Renewal", "stage": "Negotiation", "amount": 120000}], "total": 1},
    "create_case": {"id": "CASE-0011", "status": "open", "subject": "Mock Case"},
}


class SalesforcePlugin:
    connector_id = "salesforce"
    name = "Salesforce CRM"
    logo_slug = "salesforce"
    auth_scheme = "oauth2"

    def list_tools(self): return list(_TOOLS)
    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown Salesforce tool: {tool_id!r}")
        return {"connector": "salesforce", "tool": tool_id, "mode": "mock", "result": _MOCK_DATA.get(tool_id, {})}
    def test_connection(self): return {"ok": True, "message": "Salesforce mock connector is ready (mock mode)."}
