from fastapi.testclient import TestClient

from app.main import app
from app.models.flows import FlowSuggestionRequest
from app.services.audit_service import audit_service
from app.services.flow_suggestion_service import FlowSuggestionService, LiveAIRequiredError
from app.services.flow_service import flow_service
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


def _mapping_payload(mapping_id: str = "netsuite-project-to-salesforce-opportunity") -> dict:
    return {
        "mappingId": mapping_id,
        "name": "NetSuite Project to Salesforce Opportunity",
        "description": "Maps approved project fields into Salesforce opportunity fields.",
        "sourceObjectId": "netsuite-project",
        "targetObjectId": "salesforce-opportunity",
        "status": "draft",
        "mappings": [
            {
                "id": "project-to-name",
                "sourceField": "project_id",
                "targetField": "Name",
                "transform": "rename",
            },
            {
                "id": "customer-to-account",
                "sourceField": "customer_name",
                "targetField": "AccountName",
                "transform": "direct",
            },
            {
                "id": "budget-to-amount",
                "sourceField": "budget_amount",
                "targetField": "Amount",
                "transform": "direct",
            },
            {
                "id": "date-to-close",
                "sourceField": "due_date",
                "targetField": "CloseDate",
                "transform": "format_date",
            },
        ],
    }


def test_list_flows_returns_mock_catalog() -> None:
    response = client.get("/api/v1/flows")

    assert response.status_code == 200
    body = response.json()
    assert [flow["flowId"] for flow in body] == [
        "netsuite-cfo-dashboard-refresh",
        "netsuite-project-risk-refresh",
        "netsuite-subsidiary-drilldown-refresh",
    ]
    assert all(flow["sourceConnector"] == "netsuite" for flow in body)
    assert all(flow["status"] == "published" for flow in body)
    assert all(flow["lastRunAt"] is None for flow in body)
    assert all(flow["lastRunStatus"] == "never_run" for flow in body)
    assert all(flow["triggerType"] == "manual" for flow in body)


def test_get_flow_returns_steps_without_raw_query_surface() -> None:
    response = client.get("/api/v1/flows/netsuite-cfo-dashboard-refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["flowId"] == "netsuite-cfo-dashboard-refresh"
    assert body["steps"][0]["approvedTool"] == "cfo.dashboard_summary"
    assert "sql" not in body
    assert "suiteql" not in body
    assert "credential" not in body


def test_unknown_flow_returns_404_before_execution() -> None:
    response = client.get("/api/v1/flows/not-approved")

    assert response.status_code == 404


def test_run_cfo_dashboard_flow_updates_last_run_and_audit_log() -> None:
    enqueue_response = client.post("/api/v1/flows/netsuite-cfo-dashboard-refresh/run")

    assert enqueue_response.status_code == 202
    enqueue_body = enqueue_response.json()
    assert enqueue_body["requestId"]
    assert enqueue_body["flowId"] == "netsuite-cfo-dashboard-refresh"
    assert enqueue_body["status"] == "running"

    # In tests, Celery runs eagerly (CELERY_TASK_ALWAYS_EAGER=true), so the run
    # is already complete by the time we poll.
    request_id = enqueue_body["requestId"]
    body = client.get(f"/api/v1/flows/runs/{request_id}").json()
    assert body["status"] == "succeeded"
    assert body["toolsUsed"] == ["cfo.dashboard_summary", "cfo.pl_vs_budget"]
    assert body["data"]["dashboardSummary"]["mode"] == "mock"
    assert [step["status"] for step in body["executionTimeline"]] == ["succeeded", "succeeded"]
    assert body["executionTimeline"][0]["approvedTool"] == "cfo.dashboard_summary"

    flow = client.get("/api/v1/flows/netsuite-cfo-dashboard-refresh").json()
    assert flow["lastRunAt"] == body["completedAt"]
    assert flow["lastRunStatus"] == "succeeded"

    logs = client.get("/api/v1/audit/logs").json()
    assert len(logs) == 1
    assert logs[0]["requestId"] == request_id
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert logs[0]["toolsUsed"] == ["cfo.dashboard_summary", "cfo.pl_vs_budget"]
    assert logs[0]["endpointCalled"] == "/api/v1/flows/netsuite-cfo-dashboard-refresh/run"
    assert logs[0]["success"] is True
    assert "password" not in logs[0]
    assert "token" not in logs[0]
    assert "secret" not in logs[0]

    runs = client.get("/api/v1/flows/runs").json()
    assert len(runs) == 1
    assert runs[0]["requestId"] == request_id
    assert runs[0]["flowId"] == "netsuite-cfo-dashboard-refresh"
    assert runs[0]["status"] == "succeeded"
    assert runs[0]["executionTimeline"][1]["approvedTool"] == "cfo.pl_vs_budget"

    run_detail = client.get(f"/api/v1/flows/runs/{request_id}").json()
    assert run_detail["requestId"] == request_id
    assert run_detail["executionTimeline"][0]["name"] == "Load CFO summary"
    assert run_detail["inspection"]["stepCount"] == 2
    assert run_detail["inspection"]["succeededSteps"] == 2
    assert run_detail["inspection"]["auditRequestId"] == request_id


def _run_and_wait(flow_id: str) -> dict:
    enqueue = client.post(f"/api/v1/flows/{flow_id}/run")
    assert enqueue.status_code == 202
    return client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()


def test_flow_run_history_supports_filters_and_pagination() -> None:
    client.post("/api/v1/flows/netsuite-cfo-dashboard-refresh/run")
    client.post("/api/v1/flows/netsuite-project-risk-refresh/run")

    by_flow = client.get("/api/v1/flows/runs?flow_id=netsuite-project-risk-refresh").json()
    assert len(by_flow) == 1
    assert by_flow[0]["flowId"] == "netsuite-project-risk-refresh"

    by_status = client.get("/api/v1/flows/runs?run_status=succeeded").json()
    assert len(by_status) == 2

    paged = client.get("/api/v1/flows/runs?limit=1&offset=1").json()
    assert len(paged) == 1

    missing = client.get("/api/v1/flows/runs/not-a-real-run")
    assert missing.status_code == 404


def test_run_project_risk_flow_uses_approved_cfo_services() -> None:
    body = _run_and_wait("netsuite-project-risk-refresh")

    assert body["toolsUsed"] == [
        "cfo.running_projects",
        "cfo.overdue_projects_by_account_manager",
    ]
    assert body["data"]["runningProjects"]["source"] == "mock"
    assert body["data"]["overdueProjects"]["source"] == "mock"


def test_create_flow_definition_uses_approved_tools_and_writes_audit_log() -> None:
    response = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "custom-cfo-refresh",
            "name": "Custom CFO refresh",
            "description": "Refresh CFO dashboard data with approved CFO actions.",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["flowId"] == "custom-cfo-refresh"
    assert body["status"] == "draft"
    assert body["steps"][0]["approvedTool"] == "cfo.dashboard_summary"

    flows = client.get("/api/v1/flows").json()
    assert "custom-cfo-refresh" in [flow["flowId"] for flow in flows]

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "FLOW_DEFINITION"
    assert logs[0]["toolsUsed"] == ["cfo.dashboard_summary"]


def test_flow_lifecycle_requires_human_approval_before_publish() -> None:
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "approval-flow",
            "name": "Approval flow",
            "description": "Refresh CFO dashboard data with approved CFO actions.",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )

    run_before_publish_enqueue = client.post("/api/v1/flows/approval-flow/run")
    assert run_before_publish_enqueue.status_code == 202
    run_before_publish = client.get(
        f"/api/v1/flows/runs/{run_before_publish_enqueue.json()['requestId']}"
    ).json()
    assert run_before_publish["status"] == "failed"
    assert "published" in run_before_publish["message"]

    submitted = client.post(
        "/api/v1/flows/approval-flow/lifecycle",
        json={"action": "submit_for_approval"},
    ).json()
    assert submitted["flow"]["status"] == "pending_approval"

    approved = client.post(
        "/api/v1/flows/approval-flow/lifecycle",
        json={"action": "approve"},
    ).json()
    assert approved["flow"]["status"] == "approved"

    published = client.post(
        "/api/v1/flows/approval-flow/lifecycle",
        json={"action": "publish"},
    ).json()
    assert published["flow"]["status"] == "published"

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["question"] == "Flow definition action: approval-flow.publish"
    assert logs[1]["question"] == "Flow definition action: approval-flow.approve"
    assert logs[2]["question"] == "Flow definition action: approval-flow.submit_for_approval"


def test_flow_lifecycle_rejects_invalid_transition() -> None:
    response = client.post(
        "/api/v1/flows/netsuite-cfo-dashboard-refresh/lifecycle",
        json={"action": "publish"},
    )

    assert response.status_code == 409
    assert "Cannot apply publish" in response.json()["detail"]


def test_delete_custom_flow_definition_and_protect_builtin_flows() -> None:
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "delete-me-flow",
            "name": "Delete me flow",
            "description": "Temporary integration used to validate deletion.",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )

    deleted = client.delete("/api/v1/flows/delete-me-flow")
    assert deleted.status_code == 200
    assert deleted.json()["flowId"] == "delete-me-flow"

    missing = client.get("/api/v1/flows/delete-me-flow")
    assert missing.status_code == 404

    protected = client.delete("/api/v1/flows/netsuite-cfo-dashboard-refresh")
    assert protected.status_code == 409
    assert "Built-in demo integrations" in protected.json()["detail"]

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["question"] == "Flow definition action: delete-me-flow.delete"
    assert logs[0]["toolsUsed"] == ["cfo.dashboard_summary"]


def test_flow_suggestion_generates_governed_draft_and_audit_log() -> None:
    response = client.post(
        "/api/v1/flows/suggestions",
        json={
            "prompt": (
                "Create a monthly CFO dashboard refresh flow from NetSuite that compares "
                "P/L vs budget and highlights overdue projects."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["suggestedFlow"]["status"] == "draft"
    assert body["suggestedFlow"]["sourceConnector"] == "netsuite"
    assert body["suggestedFlow"]["triggerType"] == "schedule"
    assert [step["approvedTool"] for step in body["suggestedFlow"]["steps"]] == [
        "cfo.dashboard_summary",
        "cfo.pl_vs_budget",
        "cfo.overdue_projects_by_account_manager",
        "orchestrator.query",
    ]
    assert "sql" not in str(body).lower()
    assert "suiteql" not in str(body).lower()

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "FLOW_SUGGESTION"
    assert logs[0]["endpointCalled"] == "/api/v1/flows/suggestions"
    assert logs[0]["success"] is True


def test_flow_suggestion_can_require_live_ai_without_template_fallback() -> None:
    class InvalidFlowSuggestionProvider:
        provider_name = "ollama"
        model_name = "fake-local-model"

        def extract_intent(self, question: str):  # pragma: no cover
            raise NotImplementedError

        def generate_narrative(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_mapping_suggestion(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_flow_suggestion(self, context: dict):
            return type(
                "InvalidSuggestion",
                (),
                {
                    "suggested_flow": {
                        "flowId": "invalid-live-ai-flow",
                        "name": "Invalid live AI flow",
                        "description": "Invalid because it uses an unsupported raw action.",
                        "sourceConnector": "netsuite",
                        "targetModule": "cfo_dashboard",
                        "status": "draft",
                        "triggerType": "manual",
                        "steps": [
                            {
                                "id": "raw-step",
                                "name": "Raw step",
                                "description": "Invalid step.",
                                "approvedTool": "raw.system.call",
                            }
                        ],
                    },
                    "rationale": "Invalid model output for test coverage.",
                    "model_name": "fake-local-model",
                    "model_call_attempted": True,
                    "model_call_succeeded": True,
                    "provider_name": "ollama",
                },
            )()

    service = FlowSuggestionService(
        ai_provider="ollama",
        model_name="fake-local-model",
        llm_provider=InvalidFlowSuggestionProvider(),
    )

    try:
        service.suggest(
            FlowSuggestionRequest(
                prompt="Create a governed integration using real local AI.",
                requireLiveAi=True,
            )
        )
    except LiveAIRequiredError as exc:
        assert "Live AI was requested" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected live AI enforcement to reject template fallback.")


def test_flow_suggestion_falls_back_when_model_output_is_invalid() -> None:
    class InvalidFlowSuggestionProvider:
        provider_name = "ollama"
        model_name = "fake-local-model"

        def extract_intent(self, question: str):  # pragma: no cover
            raise NotImplementedError

        def generate_narrative(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_flow_suggestion(self, context: dict):
            return type(
                "InvalidSuggestion",
                (),
                {
                    "suggested_flow": {
                        "flowId": "bad-flow",
                        "name": "Bad flow",
                        "description": "Attempt to use unsupported raw access.",
                        "sourceConnector": "netsuite",
                        "targetModule": "cfo_dashboard",
                        "status": "draft",
                        "triggerType": "manual",
                        "steps": [
                            {
                                "id": "raw",
                                "name": "Raw access",
                                "description": "Unsupported step",
                                "approvedTool": "netsuite.raw_suiteql",
                            }
                        ],
                    },
                    "rationale": "Invalid model output for test coverage.",
                    "model_name": "fake-local-model",
                    "model_call_attempted": True,
                    "model_call_succeeded": True,
                    "provider_name": "ollama",
                },
            )()

    service = FlowSuggestionService(
        ai_provider="ollama",
        model_name="fake-local-model",
        llm_provider=InvalidFlowSuggestionProvider(),
    )

    response = service.suggest(
        FlowSuggestionRequest(
            prompt="Create a CFO flow for P/L budget review and overdue project risk."
        )
    )

    assert response.suggestion_fallback_used is True
    assert response.suggestion_provider == "ollama"
    assert response.suggested_flow.steps[0].approved_tool == "cfo.dashboard_summary"
    assert all("raw" not in step.approved_tool for step in response.suggested_flow.steps)


def test_flow_definition_rejects_raw_query_language_and_unapproved_tool() -> None:
    raw_query_response = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "bad-flow",
            "name": "Bad flow",
            "description": "Run select * from transaction",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "bad",
                    "name": "Bad",
                    "description": "Bad step",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )
    unapproved_tool_response = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "bad-tool-flow",
            "name": "Bad tool flow",
            "description": "Use an unsupported tool action.",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "bad",
                    "name": "Bad",
                    "description": "Bad step",
                    "approvedTool": "netsuite.raw_suiteql",
                }
            ],
        },
    )

    assert raw_query_response.status_code == 422
    assert unapproved_tool_response.status_code == 422


def test_custom_published_flow_run_fails_closed_until_runtime_mapping_exists() -> None:
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "custom-published-flow",
            "name": "Custom published flow",
            "description": "Refresh CFO dashboard data with approved CFO actions.",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )
    client.post(
        "/api/v1/flows/custom-published-flow/lifecycle",
        json={"action": "submit_for_approval"},
    )
    client.post("/api/v1/flows/custom-published-flow/lifecycle", json={"action": "approve"})
    client.post("/api/v1/flows/custom-published-flow/lifecycle", json={"action": "publish"})

    body = _run_and_wait("custom-published-flow")

    assert body["status"] == "failed"
    assert "no published mapping definition" in body["message"]
    assert body["toolsUsed"] == ["cfo.dashboard_summary"]


def test_flow_definition_rejects_unknown_or_unpublished_mapping_reference() -> None:
    unknown_response = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "mapped-flow",
            "name": "Mapped flow",
            "description": "Preview a mapped payload through approved actions.",
            "sourceConnector": "netsuite",
            "targetModule": "salesforce_opportunity",
            "status": "draft",
            "triggerType": "manual",
            "mappingDefinitionId": "missing-mapping",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )
    client.post("/api/v1/mappings/definitions", json=_mapping_payload())
    draft_mapping_response = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "draft-mapped-flow",
            "name": "Draft mapped flow",
            "description": "Preview a mapped payload through approved actions.",
            "sourceConnector": "netsuite",
            "targetModule": "salesforce_opportunity",
            "status": "draft",
            "triggerType": "manual",
            "mappingDefinitionId": "netsuite-project-to-salesforce-opportunity",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )

    assert unknown_response.status_code == 404
    assert draft_mapping_response.status_code == 409
    assert "published mapping" in draft_mapping_response.json()["detail"]


def test_custom_flow_with_published_mapping_runs_runtime_preview() -> None:
    client.post("/api/v1/mappings/definitions", json=_mapping_payload())
    client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "submit_for_approval"},
    )
    client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "approve"},
    )
    client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "publish"},
    )
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "mapped-runtime-preview",
            "name": "Mapped runtime preview",
            "description": "Preview a mapped payload through approved actions.",
            "sourceConnector": "netsuite",
            "targetModule": "salesforce_opportunity",
            "status": "draft",
            "triggerType": "manual",
            "mappingDefinitionId": "netsuite-project-to-salesforce-opportunity",
            "steps": [
                {
                    "id": "summary",
                    "name": "Load summary",
                    "description": "Load approved CFO summary data.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )
    client.post(
        "/api/v1/flows/mapped-runtime-preview/lifecycle",
        json={"action": "submit_for_approval"},
    )
    client.post("/api/v1/flows/mapped-runtime-preview/lifecycle", json={"action": "approve"})
    client.post("/api/v1/flows/mapped-runtime-preview/lifecycle", json={"action": "publish"})

    body = _run_and_wait("mapped-runtime-preview")

    assert body["status"] == "succeeded"
    assert body["data"]["mappingDefinitionId"] == "netsuite-project-to-salesforce-opportunity"
    assert body["data"]["mappingSimulation"]["targetPayload"]["AccountName"] == "Acme Manufacturing"
    assert body["data"]["mappingSimulation"]["targetPayload"]["Name"] == "PRJ-1042"
    assert body["toolsUsed"] == ["cfo.dashboard_summary"]
    assert body["executionTimeline"][0]["approvedTool"] == "cfo.dashboard_summary"
    assert body["executionTimeline"][0]["mappingDefinitionId"] == (
        "netsuite-project-to-salesforce-opportunity"
    )
    assert body["executionTimeline"][1]["id"] == "mapping-simulation"
    assert body["executionTimeline"][1]["mappingDefinitionId"] == (
        "netsuite-project-to-salesforce-opportunity"
    )
    assert body["inspection"]["mappingDefinitionId"] == (
        "netsuite-project-to-salesforce-opportunity"
    )
    assert body["inspection"]["hasSourcePayload"] is True
    assert body["inspection"]["hasTargetPayload"] is True

    saved_flow = client.get("/api/v1/flows/mapped-runtime-preview").json()
    assert saved_flow["mappingDefinitionId"] == "netsuite-project-to-salesforce-opportunity"
    assert saved_flow["lastRunStatus"] == "succeeded"

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert logs[0]["question"] == (
        "Flow run: mapped-runtime-preview using mapping netsuite-project-to-salesforce-opportunity"
    )
    assert "mapping.definition.netsuite-project-to-salesforce-opportunity" in logs[0]["toolsUsed"]


def test_run_subsidiary_flow_uses_approved_services_only() -> None:
    body = _run_and_wait("netsuite-subsidiary-drilldown-refresh")

    assert body["toolsUsed"] == ["cfo.subsidiary_drilldown", "orchestrator.query"]
    assert body["data"]["subsidiaryDrilldown"]["source"] == "mock"
    assert body["data"]["orchestratorSummary"]["detected_intent"] == "SUBSIDIARY_DRILLDOWN"

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert logs[1]["detectedIntent"] == "SUBSIDIARY_DRILLDOWN"
