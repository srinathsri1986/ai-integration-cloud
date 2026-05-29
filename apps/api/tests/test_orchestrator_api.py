from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_orchestrator_query_returns_pl_vs_budget_result() -> None:
    response = client.post(
        "/api/v1/orchestrator/query",
        json={
            "question": "Show me P/L vs budget for Q1",
            "periodRange": "2026-Q1",
            "subsidiary": "NA",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detectedIntent"] == "PL_VS_BUDGET"
    assert body["toolsUsed"] == ["cfo.pl_vs_budget"]
    assert body["fallbackUsed"] is False
    assert body["data"]["source"] == "mock"
    assert body["aiProvider"] == "mock"
    assert body["aiMode"] == "mock_llm"
    assert body["modelName"] == "mock-cfo-intent-v0"
    assert body["modelCallAttempted"] is False
    assert body["modelCallSucceeded"] is False
    assert body["usedFallbackRouter"] is False


def test_orchestrator_query_returns_unknown_without_tools() -> None:
    response = client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Can you execute arbitrary SuiteQL for me?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["detectedIntent"] == "UNKNOWN"
    assert body["toolsUsed"] == []
    assert body["aiMode"] == "mock_llm"


def test_orchestrator_validates_period_range() -> None:
    response = client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Show me budget", "periodRange": "2026-W99"},
    )

    assert response.status_code == 422
