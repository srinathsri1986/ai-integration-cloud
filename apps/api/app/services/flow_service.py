import secrets
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from app.connectors import connector_registry
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
    PaginatedFlowRuns,
    PaginatedFlows,
)
from app.repositories.flow_definition_repository import FlowDefinitionRepository
from app.repositories.flow_run_repository import FlowRunRepository
from app.services.audit_service import audit_service
from app.services.mapping_definition_service import mapping_definition_service

# These flow IDs are protected from deletion — they are the built-in demo integrations.
BUILT_IN_FLOW_IDS = {
    "demo-netsuite-cfo-dashboard",
    "demo-salesforce-opportunity-sync",
    "demo-sap-journal-post",
    "demo-oracle-financial-report",
    "demo-hcm-headcount-snapshot",
    "demo-postgres-analytics-pull",
    "demo-rest-api-webhook-relay",
    "demo-slack-alert-dispatch",
}


def _initial_flows() -> dict[str, FlowDefinition]:
    return {
        "demo-netsuite-cfo-dashboard": FlowDefinition(
            flowId="demo-netsuite-cfo-dashboard",
            name="NetSuite CFO Dashboard Refresh",
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
        "demo-salesforce-opportunity-sync": FlowDefinition(
            flowId="demo-salesforce-opportunity-sync",
            name="Salesforce Opportunity Sync",
            description="Pulls open opportunities from Salesforce CRM and lists them in the activity feed.",
            sourceConnector="salesforce",
            targetModule="crm_sync",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "list-opportunities",
                    "name": "List open opportunities",
                    "description": "Fetch open opportunities from Salesforce.",
                    "approvedTool": "list_opportunities",
                },
                {
                    "id": "get-account",
                    "name": "Enrich with account details",
                    "description": "Retrieve account details for the top opportunity.",
                    "approvedTool": "get_account",
                },
            ],
        ),
        "demo-sap-journal-post": FlowDefinition(
            flowId="demo-sap-journal-post",
            name="SAP Automated Journal Post",
            description="Posts a double-entry journal entry to SAP G/L and retrieves updated balance.",
            sourceConnector="sap",
            targetModule="gl_journal",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "post-journal",
                    "name": "Post journal entry",
                    "description": "Post a double-entry journal to the general ledger.",
                    "approvedTool": "post_journal_entry",
                },
                {
                    "id": "check-balance",
                    "name": "Check G/L balance",
                    "description": "Verify the updated G/L account balance after posting.",
                    "approvedTool": "get_gl_balance",
                },
            ],
        ),
        "demo-oracle-financial-report": FlowDefinition(
            flowId="demo-oracle-financial-report",
            name="Oracle Financial Report",
            description="Runs a pre-approved Oracle FSG report and fetches open accounting periods.",
            sourceConnector="oracle",
            targetModule="financial_reporting",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "run-report",
                    "name": "Run financial report",
                    "description": "Execute pre-approved FSG report.",
                    "approvedTool": "run_financial_report",
                },
                {
                    "id": "list-periods",
                    "name": "List open periods",
                    "description": "Retrieve open accounting periods.",
                    "approvedTool": "list_periods",
                },
            ],
        ),
        "demo-hcm-headcount-snapshot": FlowDefinition(
            flowId="demo-hcm-headcount-snapshot",
            name="HCM Headcount Snapshot",
            description="Captures current headcount and open roles from the HCM system.",
            sourceConnector="hcm",
            targetModule="workforce_analytics",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "headcount",
                    "name": "Get headcount",
                    "description": "Fetch active headcount by department.",
                    "approvedTool": "get_headcount",
                },
                {
                    "id": "open-roles",
                    "name": "List open roles",
                    "description": "Fetch open requisitions.",
                    "approvedTool": "list_open_roles",
                },
            ],
        ),
        "demo-postgres-analytics-pull": FlowDefinition(
            flowId="demo-postgres-analytics-pull",
            name="PostgreSQL Analytics Pull",
            description="Runs an approved parameterised query against the analytics database.",
            sourceConnector="postgres",
            targetModule="analytics",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "list-templates",
                    "name": "List approved query templates",
                    "description": "Show which templates are approved for execution.",
                    "approvedTool": "list_approved_templates",
                },
                {
                    "id": "run-query",
                    "name": "Run approved query",
                    "description": "Execute the revenue_by_month template.",
                    "approvedTool": "run_approved_query",
                },
            ],
        ),
        "demo-rest-api-webhook-relay": FlowDefinition(
            flowId="demo-rest-api-webhook-relay",
            name="REST API Webhook Relay",
            description="Fetches data from an approved REST endpoint and relays the response.",
            sourceConnector="rest-api",
            targetModule="webhook_relay",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "http-get",
                    "name": "Fetch from approved endpoint",
                    "description": "Execute an approved GET template to retrieve data.",
                    "approvedTool": "http_get",
                },
            ],
        ),
        "demo-slack-alert-dispatch": FlowDefinition(
            flowId="demo-slack-alert-dispatch",
            name="Slack Alert Dispatch",
            description="Posts a system alert message to the approved Slack alerts channel.",
            sourceConnector="slack",
            targetModule="alerting",
            status="published",
            triggerType="manual",
            lastRunAt=None,
            lastRunStatus="never_run",
            steps=[
                {
                    "id": "list-channels",
                    "name": "Check approved channels",
                    "description": "Verify which channels are approved for posting.",
                    "approvedTool": "list_channels",
                },
                {
                    "id": "post-alert",
                    "name": "Post alert message",
                    "description": "Send alert text to the approved alerts channel.",
                    "approvedTool": "post_message",
                },
            ],
        ),
    }


class FlowService:
    def __init__(self) -> None:
        self._lock = Lock()

    def _seed_flows(self, tenant_id: int | None = None) -> None:
        with SessionLocal() as session:
            FlowDefinitionRepository(session, tenant_id).seed_missing(list(_initial_flows().values()))

    def list_flows(
        self,
        tenant_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedFlows:
        self._seed_flows()
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)
        with SessionLocal() as session:
            repo = FlowDefinitionRepository(session, tenant_id)
            total = repo.count()
            items = repo.list_flows(limit=limit, offset=offset)
        return PaginatedFlows(items=items, total=total, limit=limit, offset=offset)

    def get_flow(self, flow_id: str, tenant_id: int | None = None) -> FlowDefinition:
        self._seed_flows()
        with SessionLocal() as session:
            return FlowDefinitionRepository(session, tenant_id).get_flow(flow_id)

    def upsert_flow(self, request: FlowDefinitionUpsertRequest, tenant_id: int | None = None) -> FlowDefinition:
        # Generate a webhook secret for any flow that might use webhook trigger
        webhook_secret = secrets.token_urlsafe(32)
        flow = FlowDefinition(
            flowId=request.flow_id,
            name=request.name,
            description=request.description,
            sourceConnector=request.source_connector,
            targetModule=request.target_module,
            status=request.status,
            triggerType=request.trigger_type,
            triggerCron=request.trigger_cron,
            webhookSecret=webhook_secret,
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
            "paused": {"submit_for_approval": "pending_approval", "unpause": "published"},
        }
        next_status = allowed.get(current_status, {}).get(action)
        if next_status is None:
            raise ValueError(f"Cannot apply {action} to a {current_status} flow.")

        return next_status

    def trigger_webhook_verified(
        self,
        flow_id: str,
        tenant_id: int | None = None,
        delivery_id: str | None = None,
    ) -> FlowRunResponse:
        """Enqueue a webhook-triggered flow run. Caller has already verified the HMAC signature.

        *delivery_id* is passed through to ``enqueue_flow_run`` so the Celery task can
        resolve the delivery record (mark succeeded/failed/dead_letter) on completion.
        """
        flow = self.get_flow(flow_id, tenant_id)
        if flow.status != "published":
            raise ValueError("Flow must be published before it can be triggered via webhook.")
        if flow.trigger_type != "webhook":
            raise ValueError("This flow is not configured for webhook triggers.")
        return self.enqueue_flow_run(flow_id, tenant_id=tenant_id, delivery_id=delivery_id)

    def trigger_webhook(self, flow_id: str, secret: str) -> FlowRunResponse:
        """Validate webhook secret and enqueue the flow run. No auth required."""
        from app.db.models import FlowDefinitionRecord
        from app.repositories.flow_definition_repository import FlowDefinitionRepository

        # Fetch with tenant_id from the record itself
        with SessionLocal() as session:
            record = session.query(FlowDefinitionRecord).filter(
                FlowDefinitionRecord.flow_id == flow_id,
                FlowDefinitionRecord.webhook_secret == secret,
            ).first()
            if record is None:
                raise KeyError(flow_id)
            tenant_id: int | None = record.tenant_id
            flow = FlowDefinitionRepository(session, tenant_id).get_flow(flow_id)

        if flow.status != "published":
            raise ValueError("Flow must be published before it can be triggered via webhook.")
        if flow.trigger_type != "webhook":
            raise ValueError("This flow is not configured for webhook triggers.")

        return self.enqueue_flow_run(flow_id, tenant_id=tenant_id)

    def enqueue_flow_run(
        self,
        flow_id: FlowId,
        tenant_id: int | None = None,
        delivery_id: str | None = None,
    ) -> FlowRunResponse:
        """Create a running record and enqueue async execution. Returns 202-style response.

        *delivery_id* is the webhook delivery tracking ID — present only for
        webhook-triggered runs, None for manual / scheduled triggers.

        Raises KeyError if *flow_id* is unknown or inaccessible for the tenant.
        """
        from app.worker.tasks import execute_flow_task

        # Guard: verify flow exists and is accessible before enqueuing.
        # Raises KeyError if not found — callers (API layer) translate this to 404.
        self.get_flow(flow_id, tenant_id=tenant_id)

        request_id = str(uuid4())
        started = datetime.now(UTC).isoformat()

        with SessionLocal() as session:
            FlowRunRepository(session, tenant_id).create_running(flow_id, request_id, started)

        # Pass delivery_id to the task so it can resolve the delivery record on completion
        execute_flow_task.delay(flow_id, request_id, tenant_id, delivery_id)

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
        """Step-driven flow execution — dispatches each step to the connector registry.

        Replaces the old hardcoded flow_id branching. Every flow is now executed the
        same way: iterate steps, resolve connector, call registry.execute_tool().
        """
        started = datetime.now(UTC).isoformat()
        timer_started = perf_counter()
        tools_used: list[str] = []
        success = False
        mapping_definition_id: str | None = None
        execution_timeline: list[FlowRunTimelineStep] = []
        data: dict = {}

        try:
            flow = self.get_flow(flow_id, tenant_id)
            mapping_definition_id = flow.mapping_definition_id

            # Gate: flow must be published
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

            # Step-driven execution: iterate steps, dispatch each to the connector registry
            step_failed = False
            for step in flow.steps:
                connector_id = step.connector_id or flow.source_connector
                tool_id = step.approved_tool
                step_start = datetime.now(UTC).isoformat()
                try:
                    result = connector_registry.execute_tool(connector_id, tool_id, params={})
                    data[step.id] = result
                    tools_used.append(tool_id)
                    execution_timeline.append(
                        self._timeline_step(
                            step_id=step.id,
                            name=step.name,
                            status="succeeded",
                            started_at=step_start,
                            approved_tool=tool_id,
                            mapping_definition_id=mapping_definition_id,
                        )
                    )
                except KeyError as exc:
                    step_failed = True
                    execution_timeline.append(
                        self._timeline_step(
                            step_id=step.id,
                            name=step.name,
                            status="failed",
                            started_at=step_start,
                            approved_tool=tool_id,
                            warnings=[f"Tool not found: {exc}"],
                        )
                    )
                    break  # stop on first step failure

            # If flow has a mapping definition, simulate it as an additional step
            if not step_failed and mapping_definition_id:
                mapping = mapping_definition_service.get_mapping(mapping_definition_id)
                if mapping.status != "published":
                    step_failed = True
                    execution_timeline.append(
                        self._timeline_step(
                            step_id="mapping-status-check",
                            name="Require published mapping",
                            status="failed",
                            started_at=started,
                            approved_tool=None,
                            mapping_definition_id=mapping_definition_id,
                            warnings=["Attached mapping definition is not published."],
                        )
                    )
                else:
                    simulation = mapping_definition_service.simulate_mapping(mapping_definition_id)
                    data["mappingSimulation"] = simulation.model_dump(by_alias=True)
                    data["mappingDefinitionId"] = mapping_definition_id
                    execution_timeline.append(
                        self._timeline_step(
                            step_id="mapping-simulation",
                            name="Simulate attached mapping",
                            status="succeeded",
                            started_at=started,
                            approved_tool=None,
                            mapping_definition_id=mapping_definition_id,
                            warnings=simulation.warnings,
                        )
                    )

            completed = datetime.now(UTC).isoformat()
            final_status = "failed" if step_failed else "succeeded"
            success = not step_failed

            response = FlowRunResponse(
                requestId=request_id,
                flowId=flow_id,
                status=final_status,
                startedAt=started,
                completedAt=completed,
                toolsUsed=tools_used,
                message=(
                    "Flow execution completed." if success
                    else "Flow execution failed on one or more steps."
                ),
                data=data,
                executionTimeline=execution_timeline,
            )
            with SessionLocal() as session:
                repo = FlowRunRepository(session, tenant_id)
                repo.update_completed(request_id, response)
                FlowDefinitionRepository(session, tenant_id).update_last_run(
                    flow_id, completed, final_status
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
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedFlowRuns:
        limit = min(max(limit, 1), 500)
        offset = max(offset, 0)
        with SessionLocal() as session:
            repo = FlowRunRepository(session, tenant_id)
            total = repo.count(flow_id=flow_id, status=status)
            items = repo.list_runs(flow_id=flow_id, status=status, limit=limit, offset=offset)
        return PaginatedFlowRuns(items=items, total=total, limit=limit, offset=offset)

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
