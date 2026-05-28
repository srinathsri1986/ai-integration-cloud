from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_summary_uses_mock_mode() -> None:
    response = client.get("/api/v1/cfo/dashboard-summary")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "mock"
    assert body["cash_position"]["currency"] == "USD"


def test_only_approved_template_runs() -> None:
    response = client.post("/api/v1/cfo/netsuite/templates/cash_position_summary/run")
    assert response.status_code == 200
    assert response.json()["source"] == "mock"

    blocked = client.post("/api/v1/cfo/netsuite/templates/select_star_from_transactions/run")
    assert blocked.status_code == 404
