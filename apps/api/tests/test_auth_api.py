from fastapi.testclient import TestClient

from app.core.auth import create_placeholder_token
from app.main import app
from app.models.auth import AuthUser


client = TestClient(app)


def token_for(role: str) -> str:
    user = AuthUser(userId="test-user", email="test@example.com", role=role)
    return create_placeholder_token(user)


def test_login_returns_placeholder_token() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "role": "Integration Admin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accessToken"]
    assert body["tokenType"] == "bearer"
    assert body["user"]["role"] == "Integration Admin"


def test_me_returns_token_user() -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for('Viewer')}"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "Viewer"


def test_viewer_can_read_audit_but_cannot_admin_connectors() -> None:
    headers = {"Authorization": f"Bearer {token_for('Viewer')}"}

    audit_response = client.get("/api/v1/audit/logs", headers=headers)
    connector_response = client.post("/api/v1/connectors/netsuite/test", headers=headers)

    assert audit_response.status_code == 200
    assert connector_response.status_code == 403


def test_cfo_can_query_orchestrator_but_cannot_run_flow() -> None:
    headers = {"Authorization": f"Bearer {token_for('CFO')}"}

    query_response = client.post(
        "/api/v1/orchestrator/query",
        json={"question": "Show dashboard summary"},
        headers=headers,
    )
    flow_response = client.post(
        "/api/v1/flows/netsuite-cfo-dashboard-refresh/run",
        headers=headers,
    )

    assert query_response.status_code == 200
    assert flow_response.status_code == 403


def test_invalid_token_is_rejected() -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
