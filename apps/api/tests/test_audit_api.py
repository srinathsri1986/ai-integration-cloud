from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service


client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()


def test_orchestrator_query_creates_audit_log() -> None:
    response = client.post(
        "/api/v1/orchestrator/query",
        json={
            "question": "Show me P/L vs budget for Q1",
            "periodRange": "2026-Q1",
            "subsidiary": "NA",
        },
    )

    assert response.status_code == 200

    logs_response = client.get("/api/v1/audit/logs")
    assert logs_response.status_code == 200
    logs = logs_response.json()

    assert len(logs) == 1
    assert logs[0]["requestId"]
    assert logs[0]["user"] == "local-dev-user"
    assert logs[0]["channel"] == "web"
    assert logs[0]["question"] == "Show me P/L vs budget for Q1"
    assert logs[0]["detectedIntent"] == "PL_VS_BUDGET"
    assert logs[0]["confidence"] == 0.91
    assert logs[0]["toolsUsed"] == ["cfo.pl_vs_budget"]
    assert logs[0]["endpointCalled"] == "/api/v1/cfo/pl-vs-budget"
    assert logs[0]["fallbackUsed"] is False
    assert logs[0]["success"] is True
    assert logs[0]["failureReason"] is None
    assert logs[0]["latencyMs"] >= 0
    assert logs[0]["aiProvider"] == "mock"
    assert logs[0]["aiMode"] == "mock_llm"
    assert logs[0]["modelName"] == "mock-cfo-intent-v0"
    assert logs[0]["modelCallAttempted"] is False
    assert logs[0]["modelCallSucceeded"] is False
    assert logs[0]["usedFallbackRouter"] is False
    assert logs[0]["narrativeProvider"] == "mock"
    assert logs[0]["narrativeModel"] == "mock-cfo-intent-v0"
    assert logs[0]["narrativeGenerated"] is True
    assert logs[0]["narrativeFallbackUsed"] is False


def test_audit_summary_aggregates_logs() -> None:
    client.post("/api/v1/orchestrator/query", json={"question": "Show dashboard summary"})
    client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Which projects are overdue by account manager?"},
    )

    response = client.get("/api/v1/audit/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["successes"] == 2
    assert body["failures"] == 0
    assert body["fallbackCount"] == 0
    assert body["averageLatencyMs"] >= 0
    assert body["byIntent"]["CFO_DASHBOARD_SUMMARY"] == 1
    assert body["byIntent"]["OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER"] == 1


def test_audit_logs_support_filters_and_pagination() -> None:
    first = client.post("/api/v1/orchestrator/query", json={"question": "Show dashboard summary"})
    client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Which projects are overdue by account manager?"},
    )
    request_id = client.get("/api/v1/audit/logs?intent=CFO_DASHBOARD_SUMMARY").json()[0][
        "requestId"
    ]

    by_intent = client.get("/api/v1/audit/logs?intent=CFO_DASHBOARD_SUMMARY").json()
    assert len(by_intent) == 1
    assert by_intent[0]["detectedIntent"] == "CFO_DASHBOARD_SUMMARY"

    by_provider = client.get("/api/v1/audit/logs?provider=mock&success=true").json()
    assert len(by_provider) == 2
    assert all(log["aiProvider"] == "mock" for log in by_provider)

    by_request = client.get(f"/api/v1/audit/logs?requestId={request_id}").json()
    assert len(by_request) == 1
    assert by_request[0]["requestId"] == request_id

    paged = client.get("/api/v1/audit/logs?limit=1&offset=1").json()
    assert len(paged) == 1
    assert first.status_code == 200


def test_unknown_orchestrator_query_logs_no_approved_tool_call() -> None:
    response = client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Can you run select * from transaction?"},
    )

    assert response.status_code == 200
    logs = client.get("/api/v1/audit/logs").json()

    assert logs[0]["detectedIntent"] == "UNKNOWN"
    assert logs[0]["toolsUsed"] == []
    assert logs[0]["endpointCalled"] == "/api/v1/orchestrator/query"
    assert "credential" not in logs[0]
    assert "secret" not in logs[0]


def test_audit_log_masks_inline_secret_values() -> None:
    response = client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Show dashboard summary password=super-secret-token"},
    )

    assert response.status_code == 200
    logs = client.get("/api/v1/audit/logs").json()

    assert "super-secret-token" not in logs[0]["question"]
    assert "password=****" in logs[0]["question"]
