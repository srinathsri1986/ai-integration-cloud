"""Oracle Fusion / E-Business Suite connector plugin (mock mode)."""
from __future__ import annotations
from ..base import ConnectorTool, ConnectorToolParam, SchemaField, SchemaObject

_TOOLS = [
    ConnectorTool("get_gl_balance", "Get G/L Balance", "Query general ledger balance for an account segment combination.", "oracle",
                  [ConnectorToolParam("ledger_id", "string", True, "Oracle ledger ID"),
                   ConnectorToolParam("account_segment", "string", True, "COA segment combination"),
                   ConnectorToolParam("period_name", "string", False, "Period name e.g. MAR-26")]),
    ConnectorTool("run_financial_report", "Run Financial Report", "Execute a pre-approved FSG or BI Publisher report.", "oracle",
                  [ConnectorToolParam("report_id", "string", True, "Approved report identifier"),
                   ConnectorToolParam("as_of_date", "string", False, "Report as-of date YYYY-MM-DD")]),
    ConnectorTool("get_subledger_entries", "Get Subledger Entries", "Retrieve journal entries from a subledger.", "oracle",
                  [ConnectorToolParam("subledger", "string", True, "AP | AR | FA | Cost Management"),
                   ConnectorToolParam("from_date", "string", False, "Start date YYYY-MM-DD"),
                   ConnectorToolParam("to_date", "string", False, "End date YYYY-MM-DD")]),
    ConnectorTool("list_periods", "List Open Periods", "List currently open accounting periods.", "oracle",
                  [ConnectorToolParam("ledger_id", "string", False, "Oracle ledger ID")]),
]
_TOOL_MAP = {t.tool_id: t for t in _TOOLS}
_MOCK = {
    "get_gl_balance": {"segment": "01-100-0000", "currency": "USD", "period": "MAR-26", "balance": 1820000},
    "run_financial_report": {"reportId": "FSG-001", "rows": [{"lineDescription": "Total Revenue", "amount": 9800000}], "generatedAt": "2026-03-31T00:00:00Z"},
    "get_subledger_entries": {"subledger": "AP", "entries": [{"entryId": "APX-001", "vendor": "Acme", "amount": 42000}]},
    "list_periods": {"periods": [{"name": "MAR-26", "status": "Open"}, {"name": "FEB-26", "status": "Closed"}]},
}


class OraclePlugin:
    connector_id = "oracle"
    name = "Oracle Fusion"
    logo_slug = "oracle"
    auth_scheme = "oauth2"

    def list_tools(self): return list(_TOOLS)
    def execute_tool(self, tool_id: str, params: dict, tenant_id: int | None = None) -> dict:
        if tool_id not in _TOOL_MAP: raise KeyError(f"Unknown Oracle tool: {tool_id!r}")
        return {"connector": "oracle", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}
    def test_connection(self): return {"ok": True, "mode": "mock", "message": "Oracle mock connector is ready (mock mode)."}
    def fetch_schema(self, tenant_id: int | None = None) -> list[SchemaObject]:
        return [
            SchemaObject("gl_balance", "GL Balance", [
                SchemaField("ledger_id", "Ledger ID", "string", required=True, sample="1"),
                SchemaField("account_segment", "Account Segment", "string", required=True, sample="01-000-1110-0000-000"),
                SchemaField("period_name", "Period Name", "string", required=True, sample="JUN-26"),
                SchemaField("entered_dr", "Entered DR", "number", sample="45000"),
                SchemaField("entered_cr", "Entered CR", "number", sample="0"),
                SchemaField("accounted_dr", "Accounted DR", "number", sample="45000"),
                SchemaField("currency_code", "Currency", "string", sample="USD"),
            ]),
            SchemaObject("legal_entity", "Legal Entity", [
                SchemaField("legal_entity_code", "Legal Entity Code", "string", required=True, sample="US01"),
                SchemaField("legal_entity_name", "Legal Entity Name", "string", required=True, sample="Acme US Operations"),
                SchemaField("currency_code", "Reporting Currency", "string", sample="USD"),
            ]),
        ]
