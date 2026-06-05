"""NetSuite connector plugin — wraps existing mock implementation."""
from __future__ import annotations

from ..base import ConnectorTool, ConnectorToolParam
from .mock_connector import MockNetSuiteConnector

_mock = MockNetSuiteConnector()

_TOOLS: list[ConnectorTool] = [
    ConnectorTool(
        tool_id="cfo.dashboard_summary",
        label="CFO Dashboard Summary",
        description="Summarised cash, AR and revenue KPIs for the CFO dashboard.",
        connector_id="netsuite",
    ),
    ConnectorTool(
        tool_id="cfo.pl_vs_budget",
        label="P/L vs Budget",
        description="Profit and loss actuals compared with approved budget.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("period", "string", False, "Reporting period e.g. 2026-Q1"),
            ConnectorToolParam("subsidiary_id", "string", False, "Subsidiary identifier"),
        ],
    ),
    ConnectorTool(
        tool_id="cfo.yoy_comparison",
        label="Year-over-Year Comparison",
        description="YoY revenue and cost comparison for CFO reporting.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("current_year", "number", False, "Current year"),
            ConnectorToolParam("prior_year", "number", False, "Prior year"),
        ],
    ),
    ConnectorTool(
        tool_id="cfo.subsidiary_drilldown",
        label="Subsidiary Drilldown",
        description="P/L breakdown by approved subsidiary.",
        connector_id="netsuite",
        params=[
            ConnectorToolParam("subsidiary_id", "string", True, "Subsidiary identifier"),
        ],
    ),
    ConnectorTool(
        tool_id="cfo.running_projects",
        label="Running Projects",
        description="List of active projects with budget and timeline status.",
        connector_id="netsuite",
    ),
    ConnectorTool(
        tool_id="cfo.overdue_projects_by_account_manager",
        label="Overdue Projects by Account Manager",
        description="Projects overdue grouped by account manager.",
        connector_id="netsuite",
    ),
]

_TOOL_MAP = {t.tool_id: t for t in _TOOLS}


class NetSuitePlugin:
    connector_id = "netsuite"
    name = "Oracle NetSuite"
    logo_slug = "netsuite"
    auth_scheme = "token_based"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown NetSuite tool: {tool_id!r}")

        # Delegate to the existing mock connector
        if tool_id == "cfo.dashboard_summary":
            from app.services.cfo_service import CfoService
            svc = CfoService()
            return svc.dashboard_summary().model_dump(by_alias=True)
        if tool_id == "cfo.pl_vs_budget":
            from app.services.cfo_service import CfoService
            svc = CfoService()
            period = params.get("period", "2026-Q1")
            sub = params.get("subsidiary_id", "NA")
            return svc.pl_vs_budget(period=period, subsidiary_id=sub).model_dump(by_alias=True)
        if tool_id == "cfo.yoy_comparison":
            from app.services.cfo_service import CfoService
            svc = CfoService()
            return svc.yoy_comparison(
                current_year=int(params.get("current_year", 2026)),
                prior_year=int(params.get("prior_year", 2025)),
                subsidiary_id=params.get("subsidiary_id", "NA"),
            ).model_dump(by_alias=True)
        if tool_id == "cfo.subsidiary_drilldown":
            from app.services.cfo_service import CfoService
            svc = CfoService()
            return svc.subsidiary_drilldown(
                period=params.get("period", "2026-Q1"),
                subsidiary_id=params.get("subsidiary_id", "EMEA"),
            ).model_dump(by_alias=True)
        if tool_id == "cfo.running_projects":
            from app.services.cfo_service import CfoService
            svc = CfoService()
            return svc.running_projects().model_dump(by_alias=True)
        if tool_id == "cfo.overdue_projects_by_account_manager":
            from app.services.cfo_service import CfoService
            svc = CfoService()
            return svc.overdue_projects_by_account_manager().model_dump(by_alias=True)

        raise KeyError(f"Unhandled NetSuite tool: {tool_id!r}")

    def test_connection(self) -> dict:
        return {"ok": True, "message": "NetSuite mock connector is ready (mock mode)."}
