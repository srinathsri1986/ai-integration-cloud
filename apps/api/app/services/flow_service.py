from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from app.models.flows import FlowDefinition, FlowId, FlowRunResponse
from app.models.orchestrator import OrchestratorQueryRequest
from app.services.audit_service import audit_service
from app.services.cfo_service import CfoService
from app.services.orchestrator_service import OrchestratorService


def _initial_flows() -> dict[str, FlowDefinition]:
    return {
        "netsuite-cfo-dashboard-refresh": FlowDefinition(
            flowId="netsuite-cfo-dashboard-refresh",
            name="NetSuite CFO dashboard refresh",
            description="Refreshes executive CFO dashboard metrics from approved mock NetSuite data.",
            sourceConnector="netsuite",
            targetModule="cfo_dashboard",
            status="active",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "summary",
                    "name": "Load CFO summary",
                    "description": "Fetch cash, receivables, revenue, and KPI summary.",
                    "approvedTool": "cfo.dashboard_summary",
                },
                {
                    "id": "budget",
                    "name": "Load P/L vs budget",
                    "description": "Fetch approved P/L vs budget mock data for 2026-Q1.",
                    "approvedTool": "cfo.pl_vs_budget",
                },
            ],
        ),
        "netsuite-project-risk-refresh": FlowDefinition(
            flowId="netsuite-project-risk-refresh",
            name="NetSuite project risk refresh",
            description="Refreshes running project exposure and overdue project risk views.",
            sourceConnector="netsuite",
            targetModule="project_risk",
            status="active",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "running-projects",
                    "name": "Load running projects",
                    "description": "Fetch active project financial exposure from approved mock data.",
                    "approvedTool": "cfo.running_projects",
                },
                {
                    "id": "overdue-projects",
                    "name": "Load overdue projects",
                    "description": "Summarize overdue projects by account manager.",
                    "approvedTool": "cfo.overdue_projects_by_account_manager",
                },
            ],
        ),
        "netsuite-subsidiary-drilldown-refresh": FlowDefinition(
            flowId="netsuite-subsidiary-drilldown-refresh",
            name="NetSuite subsidiary drilldown refresh",
            description="Refreshes subsidiary operating performance using approved mock data.",
            sourceConnector="netsuite",
            targetModule="subsidiary_drilldown",
            status="active",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "subsidiary",
                    "name": "Load subsidiary drilldown",
                    "description": "Fetch EMEA operating performance for 2026-Q1.",
                    "approvedTool": "cfo.subsidiary_drilldown",
                },
                {
                    "id": "orchestrator-summary",
                    "name": "Route CFO summary prompt",
                    "description": "Route a deterministic supported CFO summary question.",
                    "approvedTool": "orchestrator.query",
                },
            ],
        ),
    }


class FlowService:
    def __init__(
        self,
        cfo_service: CfoService | None = None,
        orchestrator_service: OrchestratorService | None = None,
    ) -> None:
        self.cfo_service = cfo_service or CfoService()
        self.orchestrator_service = orchestrator_service or OrchestratorService(self.cfo_service)
        self._lock = Lock()
        self._flows = _initial_flows()

    def list_flows(self) -> list[FlowDefinition]:
        with self._lock:
            return [flow.model_copy(deep=True) for flow in self._flows.values()]

    def get_flow(self, flow_id: str) -> FlowDefinition:
        with self._lock:
            flow = self._flows[flow_id]
            return flow.model_copy(deep=True)

    def run_flow(self, flow_id: FlowId) -> FlowRunResponse:
        request_id = str(uuid4())
        started = datetime.now(UTC).isoformat()
        timer_started = perf_counter()
        tools_used: list[str] = []
        success = False

        try:
            if flow_id == "netsuite-cfo-dashboard-refresh":
                data = {
                    "dashboardSummary": self.cfo_service.dashboard_summary().model_dump(),
                    "plVsBudget": self.cfo_service.pl_vs_budget(
                        period="2026-Q1",
                        subsidiary_id="NA",
                    ).model_dump(),
                }
                tools_used = ["cfo.dashboard_summary", "cfo.pl_vs_budget"]
            elif flow_id == "netsuite-project-risk-refresh":
                data = {
                    "runningProjects": self.cfo_service.running_projects().model_dump(),
                    "overdueProjects": self.cfo_service.overdue_projects_by_account_manager(
                        min_days_overdue=1,
                    ).model_dump(),
                }
                tools_used = [
                    "cfo.running_projects",
                    "cfo.overdue_projects_by_account_manager",
                ]
            else:
                data = {
                    "subsidiaryDrilldown": self.cfo_service.subsidiary_drilldown(
                        period="2026-Q1",
                        subsidiary_id="EMEA",
                    ).model_dump(),
                    "orchestratorSummary": self.orchestrator_service.query(
                        OrchestratorQueryRequest(
                            question="Show EMEA subsidiary drilldown",
                            periodRange="2026-Q1",
                            subsidiary="EMEA",
                        )
                    ).model_dump(),
                }
                tools_used = ["cfo.subsidiary_drilldown", "orchestrator.query"]

            completed = datetime.now(UTC).isoformat()
            with self._lock:
                flow = self._flows[flow_id].model_copy(
                    update={"last_run_at": completed, "last_run_status": "succeeded"}
                )
                self._flows[flow_id] = flow

            success = True
            return FlowRunResponse(
                requestId=request_id,
                flowId=flow_id,
                status="succeeded",
                startedAt=started,
                completedAt=completed,
                toolsUsed=tools_used,
                message="Mock flow execution completed using approved CFO services only.",
                data=data,
            )
        finally:
            latency_ms = int((perf_counter() - timer_started) * 1000)
            audit_service.record_flow_action(
                request_id=request_id,
                flow_id=flow_id,
                endpoint_called=f"/api/v1/flows/{flow_id}/run",
                tools_used=tools_used,
                success=success,
                latency_ms=latency_ms,
            )

    def clear_for_tests(self) -> None:
        with self._lock:
            self._flows = _initial_flows()


flow_service = FlowService()
