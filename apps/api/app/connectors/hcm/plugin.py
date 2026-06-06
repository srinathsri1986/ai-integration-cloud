"""HCM (Workday / SAP SuccessFactors) connector plugin (mock mode)."""
from __future__ import annotations
from ..base import ConnectorTool, ConnectorToolParam, SchemaField, SchemaObject

_TOOLS = [
    ConnectorTool("get_headcount", "Get Headcount", "Active headcount by department and location.", "hcm",
                  [ConnectorToolParam("department_id", "string", False, "Filter by department"),
                   ConnectorToolParam("as_of_date", "string", False, "As-of date YYYY-MM-DD")]),
    ConnectorTool("list_open_roles", "List Open Roles", "Open requisitions with hiring manager and target date.", "hcm",
                  [ConnectorToolParam("department_id", "string", False, "Filter by department"),
                   ConnectorToolParam("limit", "number", False, "Max records")]),
    ConnectorTool("get_department_org_chart", "Get Org Chart", "Org chart for a department showing manager hierarchy.", "hcm",
                  [ConnectorToolParam("department_id", "string", True, "Department identifier")]),
    ConnectorTool("get_compensation_bands", "Get Compensation Bands", "Approved salary bands by grade and location.", "hcm",
                  [ConnectorToolParam("grade", "string", False, "Job grade / level"),
                   ConnectorToolParam("location", "string", False, "Office location code")]),
]
_TOOL_MAP = {t.tool_id: t for t in _TOOLS}
_MOCK = {
    "get_headcount": {"total": 342, "byDepartment": {"Engineering": 140, "Sales": 80, "Finance": 45, "HR": 30, "Other": 47}},
    "list_open_roles": {"items": [{"requisitionId": "REQ-0088", "title": "Senior SWE", "department": "Engineering", "targetDate": "2026-06-01"}], "total": 1},
    "get_department_org_chart": {"departmentId": "ENG-001", "head": {"name": "Ada Lovelace", "title": "VP Engineering"}, "reports": 12},
    "get_compensation_bands": {"grade": "L5", "bands": [{"location": "US-CA", "min": 140000, "mid": 165000, "max": 195000}]},
}


class HCMPlugin:
    connector_id = "hcm"
    name = "HCM (Workday / SuccessFactors)"
    logo_slug = "hcm"
    auth_scheme = "oauth2"

    def list_tools(self): return list(_TOOLS)
    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP: raise KeyError(f"Unknown HCM tool: {tool_id!r}")
        return {"connector": "hcm", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}
    def test_connection(self): return {"ok": True, "mode": "mock", "message": "HCM mock connector is ready (mock mode)."}
    def fetch_schema(self, tenant_id: int | None = None) -> list[SchemaObject]:
        return [
            SchemaObject("employee", "Employee Record", [
                SchemaField("employee_id", "Employee ID", "string", required=True, sample="EMP-4421"),
                SchemaField("full_name", "Full Name", "string", required=True, sample="Maya Rao"),
                SchemaField("department", "Department", "string", required=True, sample="Finance"),
                SchemaField("start_date", "Start Date", "date", sample="2023-03-15"),
                SchemaField("salary", "Annual Salary", "number", sample="110000"),
                SchemaField("manager_id", "Manager ID", "string", sample="EMP-1001"),
                SchemaField("job_grade", "Job Grade", "string", sample="L5"),
                SchemaField("location", "Location", "string", sample="US-CA"),
            ]),
            SchemaObject("open_role", "Open Requisition", [
                SchemaField("requisition_id", "Requisition ID", "string", required=True, sample="REQ-0088"),
                SchemaField("title", "Job Title", "string", required=True, sample="Senior SWE"),
                SchemaField("department_id", "Department ID", "string", required=True, sample="ENG-001"),
                SchemaField("target_date", "Target Start Date", "date", sample="2026-06-01"),
                SchemaField("hiring_manager", "Hiring Manager", "string", sample="Ada Lovelace"),
            ]),
        ]
