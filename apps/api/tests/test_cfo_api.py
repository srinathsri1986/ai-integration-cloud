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


def test_pl_vs_budget_endpoint() -> None:
    response = client.get("/api/v1/cfo/pl-vs-budget?period=2026-Q1&subsidiary_id=NA")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "mock"
    assert body["period"] == "2026-Q1"
    assert len(body["lines"]) == 2


def test_yoy_comparison_endpoint() -> None:
    response = client.get(
        "/api/v1/cfo/yoy-comparison?current_year=2026&prior_year=2025&subsidiary_id=NA"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_year"] == 2026
    assert body["prior_year"] == 2025
    assert len(body["lines"]) == 2


def test_subsidiary_drilldown_endpoint_requires_subsidiary() -> None:
    response = client.get("/api/v1/cfo/subsidiary-drilldown?period=2026-Q1&subsidiary_id=EMEA")
    assert response.status_code == 200
    body = response.json()
    assert body["subsidiary_id"] == "EMEA"
    assert body["lines"][0]["subsidiary_name"] == "EMEA"


def test_running_projects_endpoint_filters_by_account_manager() -> None:
    response = client.get("/api/v1/cfo/running-projects?account_manager=Maya%20Rao")
    assert response.status_code == 200
    body = response.json()
    assert body["account_manager"] == "Maya Rao"
    assert {project["account_manager"] for project in body["projects"]} == {"Maya Rao"}


def test_overdue_projects_by_account_manager_endpoint() -> None:
    response = client.get("/api/v1/cfo/overdue-projects/by-account-manager?min_days_overdue=20")
    assert response.status_code == 200
    body = response.json()
    assert body["min_days_overdue"] == 20
    assert [manager["account_manager"] for manager in body["managers"]] == ["Maya Rao"]


def test_period_input_validation() -> None:
    response = client.get("/api/v1/cfo/pl-vs-budget?period=2026-W99")
    assert response.status_code == 422


def test_yoy_year_order_validation() -> None:
    response = client.get("/api/v1/cfo/yoy-comparison?current_year=2025&prior_year=2026")
    assert response.status_code == 422


def test_overdue_days_validation() -> None:
    response = client.get("/api/v1/cfo/overdue-projects/by-account-manager?min_days_overdue=0")
    assert response.status_code == 422
