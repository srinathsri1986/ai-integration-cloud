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
    data = response.json()
    # v5.0: paginated response wrapper
    assert "items" in data
    # Release 6.0: 8 connector-agnostic demo seed flows
    assert data["total"] == 8
    assert data["limit"] == 50
    assert data["offset"] == 0
    body = data["items"]
    flow_ids = [flow["flowId"] for flow in body]
    expected_seed_ids = {
        "demo-netsuite-cfo-dashboard",
        "demo-salesforce-opportunity-sync",
        "demo-sap-journal-post",
        "demo-oracle-financial-report",
        "demo-hcm-headcount-snapshot",
        "demo-postgres-analytics-pull",
        "demo-rest-api-webhook-relay",
        "demo-slack-alert-dispatch",
    }
    assert expected_seed_ids == set(flow_ids)
    assert all(flow["status"] == "published" for flow in body)
    assert all(flow["lastRunAt"] is None for flow in body)
    assert all(flow["lastRunStatus"] == "never_run" for flow in body)
    assert all(flow["triggerType"] == "manual" for flow in body)


def test_get_flow_returns_steps_without_raw_query_surface() -> None:
    response = client.get("/api/v1/flows/demo-netsuite-cfo-dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["flowId"] == "demo-netsuite-cfo-dashboard"
    assert body["steps"][0]["approvedTool"] == "cfo.dashboard_summary"
    assert "sql" not in body
    assert "suiteql" not in body
    assert "credential" not in body


def test_unknown_flow_returns_404_before_execution() -> None:
    response = client.get("/api/v1/flows/not-approved")

    assert response.status_code == 404


def test_run_cfo_dashboard_flow_updates_last_run_and_audit_log() -> None:
    enqueue_response = client.post("/api/v1/flows/demo-netsuite-cfo-dashboard/run")

    assert enqueue_response.status_code == 202
    enqueue_body = enqueue_response.json()
    assert enqueue_body["requestId"]
    assert enqueue_body["flowId"] == "demo-netsuite-cfo-dashboard"
    assert enqueue_body["status"] == "running"

    # In tests, Celery runs eagerly (CELERY_TASK_ALWAYS_EAGER=true), so the run
    # is already complete by the time we poll.
    request_id = enqueue_body["requestId"]
    body = client.get(f"/api/v1/flows/runs/{request_id}").json()
    assert body["status"] == "succeeded"
    assert "cfo.dashboard_summary" in body["toolsUsed"]
    assert "cfo.pl_vs_budget" in body["toolsUsed"]
    # Step-driven engine: data is keyed by step.id
    assert "summary" in body["data"]  # step id for dashboard_summary
    assert "budget" in body["data"]   # step id for pl_vs_budget
    assert [step["status"] for step in body["executionTimeline"]] == ["succeeded", "succeeded"]
    assert body["executionTimeline"][0]["approvedTool"] == "cfo.dashboard_summary"

    flow = client.get("/api/v1/flows/demo-netsuite-cfo-dashboard").json()
    assert flow["lastRunAt"] == body["completedAt"]
    assert flow["lastRunStatus"] == "succeeded"

    logs = client.get("/api/v1/audit/logs").json()
    assert len(logs) == 1
    assert logs[0]["requestId"] == request_id
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert "cfo.dashboard_summary" in logs[0]["toolsUsed"]
    assert logs[0]["endpointCalled"] == "/api/v1/flows/demo-netsuite-cfo-dashboard/run"
    assert logs[0]["success"] is True
    assert "password" not in logs[0]
    assert "token" not in logs[0]
    assert "secret" not in logs[0]

    runs_data = client.get("/api/v1/flows/runs").json()
    runs = runs_data["items"]
    assert len(runs) == 1
    assert runs[0]["requestId"] == request_id
    assert runs[0]["flowId"] == "demo-netsuite-cfo-dashboard"
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
    client.post("/api/v1/flows/demo-netsuite-cfo-dashboard/run")
    client.post("/api/v1/flows/demo-salesforce-opportunity-sync/run")

    by_flow = client.get("/api/v1/flows/runs?flow_id=demo-salesforce-opportunity-sync").json()["items"]
    assert len(by_flow) == 1
    assert by_flow[0]["flowId"] == "demo-salesforce-opportunity-sync"

    by_status = client.get("/api/v1/flows/runs?run_status=succeeded").json()["items"]
    assert len(by_status) == 2

    paged = client.get("/api/v1/flows/runs?limit=1&offset=1").json()["items"]
    assert len(paged) == 1

    missing = client.get("/api/v1/flows/runs/not-a-real-run")
    assert missing.status_code == 404


def test_run_hcm_headcount_flow_uses_registry() -> None:
    """Release 6.0: demo-hcm-headcount-snapshot executes via connector registry."""
    body = _run_and_wait("demo-hcm-headcount-snapshot")

    assert body["status"] == "succeeded"
    assert "get_headcount" in body["toolsUsed"]
    assert "list_open_roles" in body["toolsUsed"]
    # Step-driven: data keyed by step IDs
    assert "headcount" in body["data"]
    assert "open-roles" in body["data"]


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

    flows = client.get("/api/v1/flows").json()["items"]
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
        "/api/v1/flows/demo-netsuite-cfo-dashboard/lifecycle",
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

    protected = client.delete("/api/v1/flows/demo-netsuite-cfo-dashboard")
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
    """When requireLiveAi=True and the AI provider raises, LiveAIRequiredError propagates."""
    class FailingFlowSuggestionProvider:
        provider_name = "ollama"
        model_name = "fake-local-model"

        def extract_intent(self, question: str):  # pragma: no cover
            raise NotImplementedError

        def generate_narrative(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_mapping_suggestion(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_flow_suggestion(self, context: dict):
            # Simulate a hard provider failure (network error, model unavailable, etc.)
            raise RuntimeError("Fake AI provider unavailable for testing.")

    service = FlowSuggestionService(
        ai_provider="ollama",
        model_name="fake-local-model",
        llm_provider=FailingFlowSuggestionProvider(),
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
        raise AssertionError("Expected live AI enforcement to raise LiveAIRequiredError.")


def test_flow_suggestion_falls_back_when_model_provider_raises() -> None:
    """When the AI provider raises an exception (without requireLiveAi), falls back to template."""
    class FailingFlowSuggestionProvider:
        provider_name = "ollama"
        model_name = "fake-local-model"

        def extract_intent(self, question: str):  # pragma: no cover
            raise NotImplementedError

        def generate_narrative(self, context: dict):  # pragma: no cover
            raise NotImplementedError

        def generate_flow_suggestion(self, context: dict):
            raise RuntimeError("Simulated AI provider failure.")

    service = FlowSuggestionService(
        ai_provider="ollama",
        model_name="fake-local-model",
        llm_provider=FailingFlowSuggestionProvider(),
    )

    response = service.suggest(
        FlowSuggestionRequest(
            prompt="Create a CFO flow for P/L budget review and overdue project risk."
        )
    )

    assert response.suggestion_fallback_used is True
    assert response.suggestion_provider == "ollama"
    assert response.suggested_flow.steps[0].approved_tool == "cfo.dashboard_summary"


def test_flow_definition_rejects_raw_query_language_in_description() -> None:
    """Flow definitions must not contain raw SQL/SuiteQL language in description fields."""
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

    assert raw_query_response.status_code == 422


def test_custom_published_flow_with_valid_registry_tool_succeeds() -> None:
    """Release 6.0: custom flows with valid registry tools succeed without a mapping definition."""
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

    # Step-driven engine: if registry tool exists, the flow succeeds even without a mapping
    assert body["status"] == "succeeded"
    assert "cfo.dashboard_summary" in body["toolsUsed"]


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


def test_run_sap_flow_uses_registry() -> None:
    """Release 6.0: demo-sap-journal-post executes via connector registry."""
    body = _run_and_wait("demo-sap-journal-post")

    assert body["status"] == "succeeded"
    assert "post_journal_entry" in body["toolsUsed"]
    assert "get_gl_balance" in body["toolsUsed"]

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "FLOW_RUN"
    assert logs[0]["success"] is True


# ── Release 5.0 new feature tests ─────────────────────────────────────────────

def test_flow_run_history_endpoint_returns_paginated_shape() -> None:
    """GET /{flow_id}/runs returns PaginatedFlowRuns shape."""
    # Run the flow first so there is at least one run in history
    run_resp = client.post("/api/v1/flows/demo-netsuite-cfo-dashboard/run")
    assert run_resp.status_code == 202

    resp = client.get("/api/v1/flows/demo-netsuite-cfo-dashboard/runs?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["limit"] == 5
    assert body["offset"] == 0
    assert isinstance(body["items"], list)
    assert len(body["items"]) >= 1
    run = body["items"][0]
    assert "requestId" in run
    assert "flowId" in run
    assert "status" in run


def test_flow_run_history_endpoint_returns_404_for_unknown_flow() -> None:
    resp = client.get("/api/v1/flows/does-not-exist/runs")
    assert resp.status_code == 404


def test_unpause_lifecycle_restores_published_flow() -> None:
    """draft → submit_for_approval → approve → publish → pause → unpause cycles cleanly."""
    # Create a custom flow in draft state
    payload = {
        "flowId": "unpause-test-flow",
        "name": "Unpause test flow",
        "description": "Flow for testing the unpause lifecycle action.",
        "sourceConnector": "netsuite",
        "targetModule": "cfo_dashboard",
        "status": "draft",
        "triggerType": "manual",
        "steps": [
            {
                "id": "step-1",
                "name": "CFO Summary",
                "description": "Load CFO dashboard summary.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ],
    }
    create_resp = client.post("/api/v1/flows/definitions", json=payload)
    assert create_resp.status_code == 200
    flow_id = create_resp.json()["flowId"]

    # Walk the full lifecycle
    for action in ["submit_for_approval", "approve", "publish"]:
        r = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": action})
        assert r.status_code == 200, f"Action {action!r} failed: {r.text}"

    # Pause
    pause_resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "pause"})
    assert pause_resp.status_code == 200
    assert pause_resp.json()["flow"]["status"] == "paused"

    # Unpause — restores to published without re-approval
    unpause_resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "unpause"})
    assert unpause_resp.status_code == 200
    assert unpause_resp.json()["flow"]["status"] == "published"


def test_unpause_rejected_for_non_paused_flow() -> None:
    """unpause on a draft flow must return 409 (invalid transition)."""
    payload = {
        "flowId": "unpause-invalid-flow",
        "name": "Unpause invalid flow",
        "description": "Should not be unpaused from draft state.",
        "sourceConnector": "netsuite",
        "targetModule": "cfo_dashboard",
        "status": "draft",
        "triggerType": "manual",
        "steps": [
            {
                "id": "step-1",
                "name": "CFO Summary",
                "description": "Load CFO dashboard summary.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ],
    }
    create_resp = client.post("/api/v1/flows/definitions", json=payload)
    assert create_resp.status_code == 200
    flow_id = create_resp.json()["flowId"]

    resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "unpause"})
    assert resp.status_code == 409


def _create_published_webhook_flow(flow_id: str = "webhook-sig-test-flow") -> str:
    """Helper: create + publish a webhook-type flow, return its flow_id."""
    payload = {
        "flowId": flow_id,
        "name": f"Webhook signature test {flow_id}",
        "description": "Webhook-triggered flow for HMAC signature tests.",
        "sourceConnector": "netsuite",
        "targetModule": "cfo_dashboard",
        "status": "draft",
        "triggerType": "webhook",
        "webhookSecret": "test-hmac-secret",
        "steps": [
            {
                "id": "step-1",
                "name": "CFO Summary",
                "description": "Load CFO dashboard summary.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ],
    }
    r = client.post("/api/v1/flows/definitions", json=payload)
    assert r.status_code == 200, r.text
    for action in ["submit_for_approval", "approve", "publish"]:
        client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": action})
    return flow_id


def test_webhook_endpoint_returns_401_without_valid_signature() -> None:
    """POST /webhooks/{flow_id} with no signature header must return 401."""
    flow_id = _create_published_webhook_flow("webhook-nosig-flow")
    resp = client.post(
        f"/api/v1/webhooks/{flow_id}",
        content=b'{"event": "test"}',
        headers={"Content-Type": "application/json"},
    )
    # No X-Hub-Signature-256 header → 401
    assert resp.status_code == 401


def test_webhook_endpoint_returns_404_for_unknown_flow() -> None:
    resp = client.post(
        "/api/v1/webhooks/does-not-exist",
        content=b'{}',
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=badhash",
        },
    )
    assert resp.status_code == 404


def test_pagination_list_flows_respects_limit_and_offset() -> None:
    """GET /flows?limit=2&offset=0 returns at most 2 items."""
    resp = client.get("/api/v1/flows?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) <= 2
    assert body["limit"] == 2
    assert body["offset"] == 0
    assert body["total"] >= 8  # 8 seed flows always present


# ── Release 5.1 regression tests ─────────────────────────────────────────────

def _create_published_custom_flow(flow_id: str = "custom-flow-51") -> str:
    """Helper: create and publish a custom (non-seed) flow."""
    payload = {
        "flowId": flow_id,
        "name": f"Custom flow {flow_id}",
        "description": "Release 5.1 regression test custom flow.",
        "sourceConnector": "netsuite",
        "targetModule": "finance_report",
        "status": "draft",
        "triggerType": "manual",
        "steps": [
            {
                "id": "step-1",
                "name": "Summary",
                "description": "Approved summary step.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ],
    }
    r = client.post("/api/v1/flows/definitions", json=payload)
    assert r.status_code == 200, r.text
    for action in ["submit_for_approval", "approve", "publish"]:
        resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": action})
        assert resp.status_code == 200, f"Lifecycle {action} failed: {resp.text}"
    return flow_id


def test_51_global_runs_endpoint_returns_paginated_shape() -> None:
    """GET /flows/runs returns {items, total, limit, offset} — used by Dashboard (Release 5.1)."""
    resp = client.get("/api/v1/flows/runs?limit=20")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    assert body["limit"] == 20


def test_51_pause_published_custom_flow() -> None:
    """Bug 2: Pausing a custom published flow must update its status to paused."""
    flow_id = _create_published_custom_flow("custom-pause-test")
    resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "pause"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["flow"]["status"] == "paused"
    assert body["action"] == "pause"
    # Verify the status persists in GET
    get_resp = client.get(f"/api/v1/flows/{flow_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "paused"


def test_51_delete_paused_custom_flow() -> None:
    """Bug 3: A paused custom flow must be deletable (no status guard on delete)."""
    flow_id = _create_published_custom_flow("custom-delete-paused-test")
    # Pause it first
    pause_resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "pause"})
    assert pause_resp.status_code == 200
    # Then delete it
    del_resp = client.delete(f"/api/v1/flows/{flow_id}")
    assert del_resp.status_code == 200
    # Verify it's gone
    get_resp = client.get(f"/api/v1/flows/{flow_id}")
    assert get_resp.status_code == 404


def test_51_delete_builtin_flow_returns_409() -> None:
    """Built-in demo flows must not be deletable — returns 409."""
    resp = client.delete("/api/v1/flows/demo-netsuite-cfo-dashboard")
    assert resp.status_code == 409


def test_51_pause_lifecycle_response_contains_flow_with_flowid() -> None:
    """Bug 2 regression: lifecycle response body has flow.flowId (camelCase) not flow.flow_id."""
    flow_id = _create_published_custom_flow("custom-resp-shape-test")
    resp = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "pause"})
    assert resp.status_code == 200
    body = resp.json()
    # The frontend uses response.data.flow.flowId — must be camelCase
    assert "flowId" in body["flow"], "Expected camelCase 'flowId' in lifecycle response body"
    assert "flow_id" not in body["flow"], "Unexpected snake_case 'flow_id' in lifecycle response"


# ─── R16 — Flow Run History & Replay ─────────────────────────────────────────

def test_r16_replay_returns_202_with_new_request_id() -> None:
    """POST /flows/runs/{request_id}/replay → 202 with a fresh requestId distinct from original."""
    flow_id = _create_published_custom_flow("replay-test-flow")
    # Trigger an initial run
    run_resp = client.post(f"/api/v1/flows/{flow_id}/run")
    assert run_resp.status_code == 202, run_resp.text
    original_request_id = run_resp.json()["requestId"]

    # Replay it
    replay_resp = client.post(f"/api/v1/flows/runs/{original_request_id}/replay")
    assert replay_resp.status_code == 202, replay_resp.text
    body = replay_resp.json()
    assert "requestId" in body
    assert body["requestId"] != original_request_id, "Replay must produce a new requestId"
    assert body["flowId"] == flow_id


def test_r16_replay_of_unknown_run_returns_404() -> None:
    """POST /flows/runs/{unknown_id}/replay → 404 with meaningful detail."""
    resp = client.post("/api/v1/flows/runs/does-not-exist-run/replay")
    assert resp.status_code == 404
    body = resp.json()
    assert "detail" in body
    assert "not found" in body["detail"].lower()


def test_r16_replay_deleted_flow_returns_404() -> None:
    """If the source flow was deleted after the run, replay returns 404 for the flow."""
    flow_id = _create_published_custom_flow("replay-deleted-flow")
    run_resp = client.post(f"/api/v1/flows/{flow_id}/run")
    assert run_resp.status_code == 202, run_resp.text
    original_request_id = run_resp.json()["requestId"]

    # Pause then delete the flow
    client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": "pause"})
    del_resp = client.delete(f"/api/v1/flows/{flow_id}")
    assert del_resp.status_code == 200, del_resp.text

    # Replay should now 404 on the flow
    replay_resp = client.post(f"/api/v1/flows/runs/{original_request_id}/replay")
    assert replay_resp.status_code == 404


def test_r16_replay_creates_new_audit_entry() -> None:
    """Replaying a run should produce a new audit log entry."""
    flow_id = _create_published_custom_flow("replay-audit-flow")
    run_resp = client.post(f"/api/v1/flows/{flow_id}/run")
    original_request_id = run_resp.json()["requestId"]

    # Count audit entries before replay
    audit_before = client.get("/api/v1/audit/logs")
    count_before = len(audit_before.json())

    client.post(f"/api/v1/flows/runs/{original_request_id}/replay")

    audit_after = client.get("/api/v1/audit/logs")
    count_after = len(audit_after.json())
    assert count_after > count_before, "Replay must produce at least one new audit entry"


def test_r16_replay_response_shape_has_required_fields() -> None:
    """Replay response body conforms to FlowRunResponse shape expected by the frontend."""
    flow_id = _create_published_custom_flow("replay-shape-flow")
    run_resp = client.post(f"/api/v1/flows/{flow_id}/run")
    original_request_id = run_resp.json()["requestId"]

    replay_resp = client.post(f"/api/v1/flows/runs/{original_request_id}/replay")
    assert replay_resp.status_code == 202, replay_resp.text
    body = replay_resp.json()

    required_fields = {"requestId", "flowId", "status", "startedAt", "message"}
    for field in required_fields:
        assert field in body, f"Missing field '{field}' in replay response"

    # Status must be a valid run status
    assert body["status"] in {"running", "queued", "succeeded", "failed"}


def test_r16_multiple_replays_produce_distinct_run_ids() -> None:
    """Replaying the same original run twice must yield two distinct new run IDs."""
    flow_id = _create_published_custom_flow("replay-multi-flow")
    run_resp = client.post(f"/api/v1/flows/{flow_id}/run")
    original_request_id = run_resp.json()["requestId"]

    r1 = client.post(f"/api/v1/flows/runs/{original_request_id}/replay").json()
    r2 = client.post(f"/api/v1/flows/runs/{original_request_id}/replay").json()

    assert r1["requestId"] != r2["requestId"], "Each replay must produce a unique requestId"
    assert r1["requestId"] != original_request_id
    assert r2["requestId"] != original_request_id
