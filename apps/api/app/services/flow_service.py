from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.flows import (
    FlowDefinition,
    FlowDefinitionUpsertRequest,
    FlowId,
    FlowRunInspection,
    FlowLifecycleAction,
    FlowLifecycleResponse,
    FlowRunResponse,
    FlowRunTimelineStep,
)
from app.models.orchestrator import OrchestratorQueryRequest
from app.repositories.flow_definition_repository import FlowDefinitionRepository
from app.repositories.flow_run_repository import FlowRunRepository
from app.services.audit_service import audit_service
from app.services.cfo_service import CfoService
from app.services.mapping_definition_service import mapping_definition_service
from app.services.orchestrator_service import OrchestratorService

BUILT_IN_FLOW_IDS = {
    "netsuite-cfo-dashboard-refresh",
    "netsuite-project-risk-refresh",
    "netsuite-subsidiary-drilldown-refresh",
}


def _initial_flows() -> dict[str, FlowDefinition]:
    return {
        "netsuite-cfo-dashboard-refresh": FlowDefinition(
            flowId="netsuite-cfo-dashboard-refresh",
            name="NetSuite CFO dashboard refresh",
            description="Refreshes executive CFO dashboard metrics from approved mock NetSuite data.",
            sourceConnector="netsuite",
            targetModule="cfo_dashboard",
            status="published",
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
            status="published",
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
            status="published",
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

    def _seed_flows(self, tenant_id: int | None = None) -> None:
        with SessionLocal() as session:
            FlowDefinitionRepository(session, tenant_id).seed_missing(list(_initial_flows().values()))

    def list_flows(self, tenant_id: int | None = None) -> list[FlowDefinition]:
        self._seed_flows()
        with SessionLocal() as session:
            return FlowDefinitionRepository(session, tenant_id).list_flows()

    def get_flow(self, flow_id: str, tenant_id: int | None = None) -> FlowDefinition:
        self._seed_flows()
        with SessionLocal() as session:
            return FlowDefinitionRepository(session, tenant_id).get_flow(flow_id)

    def upsert_flow(self, request: FlowDefinitionUpsertRequest, tenant_id: int | None = None) -> FlowDefinition:
        flow = FlowDefinition(
            flowId=request.flow_id,
            name=request.name,
            description=request.description,
            sourceConnector=request.source_connector,
            targetModule=request.target_module,
            status=request.status,
            triggerType=request.trigger_type,
            mappingDefinitionId=request.mapping_definition_id,
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=request.steps,
        )
        if request.mapping_definition_id:
            mapping = mapping_definition_service.get_mapping(request.mapping_definition_id)
            if mapping.status != "published":
                raise ValueError("Flow mappingDefinitionId must reference a published mapping.")

        with SessionLocal() as session:
            saved = FlowDefinitionRepository(session, tenant_id).upsert(flow)

        audit_service.record_flow_definition_action(
            flow_id=saved.flow_id,
            action="upsert",
            tools_used=[step.approved_tool for step in saved.steps],
        )
        return saved

    def transition_flow(
        self,
        flow_id: str,
        action: FlowLifecycleAction,
        note: str | None = None,
        tenant_id: int | None = None,
    ) -> FlowLifecycleResponse:
        flow = self.get_flow(flow_id, tenant_id)
        next_status = self._next_status(flow.status, action)

        with SessionLocal() as session:
            updated = FlowDefinitionRepository(session, tenant_id).update_status(flow_id, next_status)

        audit_service.record_flow_definition_action(
            flow_id=updated.flow_id,
            action=action,
            tools_used=[step.approved_tool for step in updated.steps],
        )
        note_suffix = f" Note: {note}" if note else ""
        return FlowLifecycleResponse(
            flow=updated,
            action=action,
            message=f"{updated.name} moved to {next_status}.{note_suffix}",
        )

    def delete_flow(self, flow_id: str, tenant_id: int | None = None) -> dict[str, str]:
        if flow_id in BUILT_IN_FLOW_IDS:
            raise ValueError("Built-in demo integrations cannot be deleted.")

        flow = self.get_flow(flow_id, tenant_id)
        with SessionLocal() as session:
            FlowDefinitionRepository(session, tenant_id).delete_flow(flow_id)

        audit_service.record_flow_definition_action(
            flow_id=flow.flow_id,
            action="delete",
            tools_used=[step.approved_tool for step in flow.steps],
        )
        return {
            "flowId": flow_id,
            "message": "Integration deleted.",
        }

    def _next_status(self, current_status: str, action: FlowLifecycleAction) -> str:
        allowed = {
            "draft": {"submit_for_approval": "pending_approval", "pause": "paused"},
            "pending_approval": {"approve": "approved", "reject": "draft", "pause": "paused"},
            "approved": {"publish": "published", "reject": "draft", "pause": "paused"},
            "published": {"pause": "paused"},
            "paused": {"submit_for_approval": "pending_approval"},
        }
        next_status = allowed.get(current_status, {}).get(action)
        if next_status is None:
            raise ValueError(f"Cannot apply {action} to a {current_status} flow.")

        return next_status

    def enqueue_flow_run(self, flow_id: FlowId, tenant_id: int | None = None) -> FlowRunResponse:
        """Create a running record and enqueue async execution. Returns 202-style response."""
        from app.worker.tasks import execute_flow_task

        request_id = str(uuid4())
        started = datetime.now(UTC).isoformat()

        with SessionLocal() as session:
            FlowRunRepository(session, tenant_id).create_running(flow_id, request_id, started)

        execute_flow_task.delay(flow_id, request_id, tenant_id)

        return FlowRunResponse(
            requestId=request_id,
            flowId=flow_id,
            status="running",
            startedAt=started,
            completedAt=None,
            toolsUsed=[],
            message="Flow execution enqueued.",
            data={},
            executionTimeline=[],
        )

    def _mark_run_dead_letter(
        self, request_id: str, tenant_id: int | None, message: str
    ) -> None:
        completed = datetime.now(UTC).isoformat()
        with SessionLocal() as session:
            repo = FlowRunRepository(session, tenant_id)
            existing = repo.get_by_request_id(request_id)
            dead = FlowRunResponse(
                requestId=request_id,
                flowId=existing.flow_id,
                status="failed",
                startedAt=existing.started_at,
                completedAt=completed,
                toolsUsed=[],
                message=message,
                data={},
                executionTimeline=[],
            )
            repo.update_completed(request_id, dead)

    def _execute_flow_sync(
        self, flow_id: FlowId, request_id: str, tenant_id: int | None = None
    ) -> None:
        """Run flow synchronously and update the existing run record. Called by Celery task."""
        started = datetime.now(UTC).isoformat()
        timer_started = perf_counter()
        tools_used: list[str] = []
        success = False
        mapping_definition_id: str | None = None
        execution_timeline: list[FlowRunTimelineStep] = []

        try:
            flow = self.get_flow(flow_id, tenant_id)
            mapping_definition_id = flow.mapping_definition_id
            if flow.status != "published":
                completed = datetime.now(UTC).isoformat()
                response = FlowRunResponse(
                    requestId=request_id,
                    flowId=flow_id,
                    status="failed",
                    startedAt=started,
                    completedAt=completed,
                    toolsUsed=[],
                    message="Flow must be published before it can be run.",
                    data={},
                    executionTimeline=[
                        self._timeline_step(
                            step_id="publish-check",
                            name="Require published flow",
                            status="failed",
                            started_at=started,
                            approved_tool=None,
                            warnings=["Flow must be published before it can be run."],
                        )
                    ],
                )
                with SessionLocal() as session:
                    FlowRunRepository(session, tenant_id).update_completed(request_id, response)
                return

            if flow_id == "netsuite-cfo-dashboard-refresh":
                data = {
                    "dashboardSummary": self.cfo_service.dashboard_summary().model_dump(),
                    "plVsBudget": self.cfo_service.pl_vs_budget(
                        period="2026-Q1",
                        subsidiary_id="NA",
                    ).model_dump(),
                }
                tools_used = ["cfo.dashboard_summary", "cfo.pl_vs_budget"]
                execution_timeline = self._timeline_for_tools(flow, tools_used, started)
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
                execution_timeline = self._timeline_for_tools(flow, tools_used, started)
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
                execution_timeline = self._timeline_for_tools(flow, tools_used, started)
            else:
                completed = datetime.now(UTC).isoformat()
                tools_used = [step.approved_tool for step in flow.steps]
                if flow.mapping_definition_id is None:
                    response = FlowRunResponse(
                        requestId=request_id,
                        flowId=flow_id,
                        status="failed",
                        startedAt=started,
                        completedAt=completed,
                        toolsUsed=tools_used,
                        message=(
                            "Flow definition is saved, but no published mapping definition "
                            "is attached for custom runtime preview."
                        ),
                        data={"steps": [step.model_dump(by_alias=True) for step in flow.steps]},
                        executionTimeline=[
                            self._timeline_step(
                                step_id="mapping-check",
                                name="Require attached published mapping",
                                status="failed",
                                started_at=started,
                                approved_tool=None,
                                warnings=["No published mapping definition is attached."],
                            )
                        ],
                    )
                    with SessionLocal() as session:
                        repo = FlowRunRepository(session, tenant_id)
                        repo.update_completed(request_id, response)
                        FlowDefinitionRepository(session, tenant_id).update_last_run(
                            flow_id, completed, "failed"
                        )
                    return

                mapping = mapping_definition_service.get_mapping(flow.mapping_definition_id)
                if mapping.status != "published":
                    response = FlowRunResponse(
                        requestId=request_id,
                        flowId=flow_id,
                        status="failed",
                        startedAt=started,
                        completedAt=completed,
                        toolsUsed=tools_used,
                        message="Attached mapping definition must be published before flow runtime preview.",
                        data={"mappingDefinitionId": flow.mapping_definition_id},
                        executionTimeline=[
                            self._timeline_step(
                                step_id="mapping-status-check",
                                name="Require published mapping",
                                status="failed",
                                started_at=started,
                                approved_tool=None,
                                mapping_definition_id=flow.mapping_definition_id,
                                warnings=["Attached mapping definition is not published."],
                            )
                        ],
                    )
                    with SessionLocal() as session:
                        repo = FlowRunRepository(session, tenant_id)
                        repo.update_completed(request_id, response)
                        FlowDefinitionRepository(session, tenant_id).update_last_run(
                            flow_id, completed, "failed"
                        )
                    return

                simulation = mapping_definition_service.simulate_mapping(flow.mapping_definition_id)
                execution_timeline = self._timeline_for_tools(
                    flow,
                    tools_used,
                    started,
                    mapping_definition_id=flow.mapping_definition_id,
                )
                execution_timeline.append(
                    self._timeline_step(
                        step_id="mapping-simulation",
                        name="Simulate attached mapping",
                        status="succeeded",
                        started_at=started,
                        approved_tool=None,
                        mapping_definition_id=flow.mapping_definition_id,
                        warnings=simulation.warnings,
                    )
                )
                success = True
                completed = datetime.now(UTC).isoformat()
                response = FlowRunResponse(
                    requestId=request_id,
                    flowId=flow_id,
                    status="succeeded",
                    startedAt=started,
                    completedAt=completed,
                    toolsUsed=tools_used,
                    message="Custom flow runtime preview completed using the attached published mapping.",
                    data={
                        "steps": [step.model_dump(by_alias=True) for step in flow.steps],
                        "mappingDefinitionId": flow.mapping_definition_id,
                        "mappingSimulation": simulation.model_dump(by_alias=True),
                    },
                    executionTimeline=execution_timeline,
                )
                with SessionLocal() as session:
                    repo = FlowRunRepository(session, tenant_id)
                    repo.update_completed(request_id, response)
                    FlowDefinitionRepository(session, tenant_id).update_last_run(
                        flow_id, completed, "succeeded"
                    )
                return

            completed = datetime.now(UTC).isoformat()
            with SessionLocal() as session:
                FlowDefinitionRepository(session, tenant_id).update_last_run(
                    flow_id, completed, "succeeded"
                )

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
                executionTimeline=execution_timeline,
            )
            with SessionLocal() as session:
                FlowRunRepository(session, tenant_id).update_completed(request_id, response)

        finally:
            latency_ms = int((perf_counter() - timer_started) * 1000)
            audit_service.record_flow_action(
                request_id=request_id,
                flow_id=flow_id,
                endpoint_called=f"/api/v1/flows/{flow_id}/run",
                tools_used=tools_used,
                success=success,
                latency_ms=latency_ms,
                mapping_definition_id=mapping_definition_id,
            )

    def clear_for_tests(self, tenant_id: int | None = None) -> None:
        with SessionLocal() as session:
            FlowRunRepository(session, tenant_id).clear()
            FlowDefinitionRepository(session, tenant_id).clear()

        self._seed_flows()

    def list_runs(
        self,
        tenant_id: int | None = None,
        *,
        flow_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FlowRunResponse]:
        with SessionLocal() as session:
            return FlowRunRepository(session, tenant_id).list_runs(
                flow_id=flow_id,
                status=status,
                limit=limit,
                offset=offset,
            )

    def get_run(self, request_id: str, tenant_id: int | None = None) -> FlowRunResponse:
        with SessionLocal() as session:
            return FlowRunRepository(session, tenant_id).get_by_request_id(request_id)

    def _with_inspection(self, response: FlowRunResponse) -> FlowRunResponse:
        mapping_simulation = response.data.get("mappingSimulation") if isinstance(response.data, dict) else None
        mapping_definition_id = response.data.get("mappingDefinitionId") if isinstance(response.data, dict) else None
        if not mapping_definition_id:
            mapping_definition_id = next(
                (step.mapping_definition_id for step in response.execution_timeline if step.mapping_definition_id),
                None,
            )

        response.inspection = FlowRunInspection(
            durationMs=self._duration_ms(response.started_at, response.completed_at),
            stepCount=len(response.execution_timeline),
            succeededSteps=sum(1 for step in response.execution_timeline if step.status == "succeeded"),
            failedSteps=sum(1 for step in response.execution_timeline if step.status == "failed"),
            skippedSteps=sum(1 for step in response.execution_timeline if step.status == "skipped"),
            warningCount=sum(len(step.warnings) for step in response.execution_timeline),
            mappingDefinitionId=mapping_definition_id,
            hasSourcePayload=bool(
                isinstance(mapping_simulation, dict) and mapping_simulation.get("sourcePayload")
            ),
            hasTargetPayload=bool(
                isinstance(mapping_simulation, dict) and mapping_simulation.get("targetPayload")
            ),
            auditRequestId=response.request_id,
        )
        return response

    def _duration_ms(self, started_at: str, completed_at: str) -> int:
        try:
            started = datetime.fromisoformat(started_at)
            completed = datetime.fromisoformat(completed_at)
        except ValueError:
            return 0

        return max(0, int((completed - started).total_seconds() * 1000))

    def _timeline_for_tools(
        self,
        flow: FlowDefinition,
        tools_used: list[str],
        started_at: str,
        mapping_definition_id: str | None = None,
    ) -> list[FlowRunTimelineStep]:
        timeline: list[FlowRunTimelineStep] = []
        used_set = set(tools_used)

        for step in flow.steps:
            timeline.append(
                self._timeline_step(
                    step_id=step.id,
                    name=step.name,
                    status="succeeded" if step.approved_tool in used_set else "skipped",
                    started_at=started_at,
                    approved_tool=step.approved_tool,
                    mapping_definition_id=mapping_definition_id,
                )
            )

        return timeline

    def _timeline_step(
        self,
        *,
        step_id: str,
        name: str,
        status: str,
        started_at: str,
        approved_tool: str | None,
        mapping_definition_id: str | None = None,
        warnings: list[str] | None = None,
    ) -> FlowRunTimelineStep:
        completed_at = datetime.now(UTC).isoformat()
        return FlowRunTimelineStep(
            id=step_id,
            name=name,
            status=status,
            startedAt=started_at,
            completedAt=completed_at,
            latencyMs=0,
            approvedTool=approved_tool,
            mappingDefinitionId=mapping_definition_id,
            warnings=warnings or [],
        )


flow_service = FlowService()
