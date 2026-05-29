from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.flows import FlowDefinition, FlowDefinitionUpsertRequest, FlowId, FlowRunResponse
from app.models.orchestrator import OrchestratorQueryRequest
from app.repositories.flow_definition_repository import FlowDefinitionRepository
from app.repositories.flow_run_repository import FlowRunRepository
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
            triggerType="manual",
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
            triggerType="manual",
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
            triggerType="manual",
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
        self._seed_flows()

    def _seed_flows(self) -> None:
        with SessionLocal() as session:
            FlowDefinitionRepository(session).seed_missing(list(_initial_flows().values()))

    def list_flows(self) -> list[FlowDefinition]:
        self._seed_flows()
        with SessionLocal() as session:
            return FlowDefinitionRepository(session).list_flows()

    def get_flow(self, flow_id: str) -> FlowDefinition:
        self._seed_flows()
        with SessionLocal() as session:
            return FlowDefinitionRepository(session).get_flow(flow_id)

    def upsert_flow(self, request: FlowDefinitionUpsertRequest) -> FlowDefinition:
        flow = FlowDefinition(
            flowId=request.flow_id,
            name=request.name,
            description=request.description,
            sourceConnector=request.source_connector,
            targetModule=request.target_module,
            status=request.status,
            triggerType=request.trigger_type,
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=request.steps,
        )
        with SessionLocal() as session:
            saved = FlowDefinitionRepository(session).upsert(flow)

        audit_service.record_flow_definition_action(
            flow_id=saved.flow_id,
            action="upsert",
            tools_used=[step.approved_tool for step in saved.steps],
        )
        return saved

    def run_flow(self, flow_id: FlowId) -> FlowRunResponse:
        request_id = str(uuid4())
        started = datetime.now(UTC).isoformat()
        timer_started = perf_counter()
        tools_used: list[str] = []
        success = False

        try:
            flow = self.get_flow(flow_id)
            if flow.status != "active":
                completed = datetime.now(UTC).isoformat()
                response = FlowRunResponse(
                    requestId=request_id,
                    flowId=flow_id,
                    status="failed",
                    startedAt=started,
                    completedAt=completed,
                    toolsUsed=[],
                    message="Flow is not active and cannot be run.",
                    data={},
                )
                with SessionLocal() as session:
                    FlowRunRepository(session).append(response)
                return response

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
            elif flow_id == "netsuite-subsidiary-drilldown-refresh":
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
            else:
                completed = datetime.now(UTC).isoformat()
                tools_used = [step.approved_tool for step in flow.steps]
                response = FlowRunResponse(
                    requestId=request_id,
                    flowId=flow_id,
                    status="failed",
                    startedAt=started,
                    completedAt=completed,
                    toolsUsed=tools_used,
                    message=(
                        "Flow definition is saved, but executable runtime mapping is not "
                        "enabled for custom flows yet."
                    ),
                    data={"steps": [step.model_dump(by_alias=True) for step in flow.steps]},
                )
                with SessionLocal() as session:
                    FlowRunRepository(session).append(response)
                    FlowDefinitionRepository(session).update_last_run(flow_id, completed, "failed")
                return response

            completed = datetime.now(UTC).isoformat()
            with SessionLocal() as session:
                FlowDefinitionRepository(session).update_last_run(flow_id, completed, "succeeded")

            success = True
            response = FlowRunResponse(
                requestId=request_id,
                flowId=flow_id,
                status="succeeded",
                startedAt=started,
                completedAt=completed,
                toolsUsed=tools_used,
                message="Mock flow execution completed using approved CFO services only.",
                data=data,
            )
            with SessionLocal() as session:
                FlowRunRepository(session).append(response)

            return response
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
        with SessionLocal() as session:
            FlowRunRepository(session).clear()
            FlowDefinitionRepository(session).clear()

        self._seed_flows()

    def list_runs(
        self,
        *,
        flow_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FlowRunResponse]:
        with SessionLocal() as session:
            return FlowRunRepository(session).list_runs(
                flow_id=flow_id,
                status=status,
                limit=limit,
                offset=offset,
            )


flow_service = FlowService()
