from fastapi.testclient import TestClient

from app.main import app
from app.models.flows import FlowSuggestionRequest
from app.services.audit_service import audit_service
from app.services.flow_suggestion_service import FlowSuggestionService
from app.services.flow_service import flow_service


client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()


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
    assert all(flow["status"] == "active" for flow in body)
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
    response = client.post("/api/v1/flows/netsuite-cfo-dashboard-refresh/run")

    assert response.status_code == 200
    body = response.json()
    assert body["requestId"]
    assert body["flowId"] == "netsuite-cfo-dashboard-refresh"
    assert body["status"] == "succeeded"
    assert body["toolsUsed"] == ["cfo.dashboard_summary", "cfo.pl_vs_budget"]
    assert body["data"]["dashboardSummary"]["mode"] == "mock"

    flow = client.get("/api/v1/flows/netsuite-cfo-dashboard-refresh").json()
    assert flow["lastRunAt"] == body["completedAt"]
    assert flow["lastRunStatus"] == "succeeded"

    logs = client.get("/api/v1/audit/logs").json()
    assert len(logs) == 1
    assert logs[0]["requestId"] == body["requestId"]
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert logs[0]["toolsUsed"] == ["cfo.dashboard_summary", "cfo.pl_vs_budget"]
    assert logs[0]["endpointCalled"] == "/api/v1/flows/netsuite-cfo-dashboard-refresh/run"
    assert logs[0]["success"] is True
    assert "password" not in logs[0]
    assert "token" not in logs[0]
    assert "secret" not in logs[0]

    runs = client.get("/api/v1/flows/runs").json()
    assert len(runs) == 1
    assert runs[0]["requestId"] == body["requestId"]
    assert runs[0]["flowId"] == "netsuite-cfo-dashboard-refresh"
    assert runs[0]["status"] == "succeeded"


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


def test_run_project_risk_flow_uses_approved_cfo_services() -> None:
    response = client.post("/api/v1/flows/netsuite-project-risk-refresh/run")

    assert response.status_code == 200
    body = response.json()
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
    assert body["suggestedFlow"]["triggerType"] == "schedule_placeholder"
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


def test_custom_flow_run_fails_closed_until_runtime_mapping_exists() -> None:
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "custom-active-flow",
            "name": "Custom active flow",
            "description": "Refresh CFO dashboard data with approved CFO actions.",
            "sourceConnector": "netsuite",
            "targetModule": "cfo_dashboard",
            "status": "active",
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

    response = client.post("/api/v1/flows/custom-active-flow/run")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert "runtime mapping is not enabled" in body["message"]
    assert body["toolsUsed"] == ["cfo.dashboard_summary"]


def test_run_subsidiary_flow_uses_approved_services_only() -> None:
    response = client.post("/api/v1/flows/netsuite-subsidiary-drilldown-refresh/run")

    assert response.status_code == 200
    body = response.json()
    assert body["toolsUsed"] == ["cfo.subsidiary_drilldown", "orchestrator.query"]
    assert body["data"]["subsidiaryDrilldown"]["source"] == "mock"
    assert body["data"]["orchestratorSummary"]["detected_intent"] == "SUBSIDIARY_DRILLDOWN"

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert logs[1]["detectedIntent"] == "SUBSIDIARY_DRILLDOWN"
