from fastapi.testclient import TestClient

from app.core.auth import create_placeholder_token
from app.main import app
from app.models.auth import AuthUser


client = TestClient(app)


def token_for(role: str) -> str:
    user = AuthUser(userId="test-user", email="test@example.com", role=role)
    return create_placeholder_token(user)


# --- Placeholder login (dev/test endpoint) ---

def test_placeholder_login_returns_token() -> None:
    response = client.post(
        "/api/v1/auth/login/placeholder",
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


# --- Real auth endpoints ---

def test_register_creates_user() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "SecurePass1", "role": "Developer"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert "verify" in body["message"].lower()


def test_register_duplicate_email_rejected() -> None:
    payload = {"email": "duplicate@example.com", "password": "SecurePass1", "role": "Developer"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_register_weak_password_rejected() -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_unverified_user_rejected() -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "unverified@example.com", "password": "SecurePass1", "role": "Developer"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@example.com", "password": "SecurePass1"},
    )
    assert response.status_code == 403


def test_login_wrong_password_rejected() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "anyone@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401


def test_forgot_password_always_returns_200() -> None:
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "doesnotexist@example.com"},
    )
    assert response.status_code == 200
    assert "reset link" in response.json()["message"].lower()


def test_reset_password_invalid_token_rejected() -> None:
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "invalid-token", "password": "NewSecure1"},
    )
    assert response.status_code == 400


def test_logout_clears_cookie() -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out."
