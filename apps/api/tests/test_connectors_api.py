from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.audit_service import audit_service
from app.services.connector_config_service import connector_config_service


client = TestClient(app)


def setup_function() -> None:
    get_settings.cache_clear()
    audit_service.clear_for_tests()
    connector_config_service.clear_for_tests()


def teardown_function() -> None:
    get_settings.cache_clear()
    connector_config_service.clear_for_tests()


def test_list_connectors_includes_mock_netsuite_connector() -> None:
    response = client.get("/api/v1/connectors")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "id": "netsuite",
            "name": "NetSuite",
            "status": "not_configured",
            "mockMode": True,
            "mode": "mock",
            "lastTestedAt": None,
        }
    ]


def test_get_netsuite_config_returns_placeholder_only_config() -> None:
    response = client.get("/api/v1/connectors/netsuite")

    assert response.status_code == 200
    body = response.json()
    assert body["accountId"] == "MOCK-ACCOUNT"
    assert body["environment"] == "sandbox"
    assert body["authMode"] == "placeholder"
    assert body["mockMode"] is True
    assert body["mode"] == "mock"
    assert body["status"] == "not_configured"
    assert body["lastTestedAt"] is None
    assert body["baseUrlConfigured"] is False
    assert body["credentialsConfigured"] is False
    assert "password" not in body
    assert "token" not in body
    assert "secret" not in body


def test_update_netsuite_config_stores_only_placeholder_fields() -> None:
    response = client.put(
        "/api/v1/connectors/netsuite/config",
        json={
            "accountId": "MOCK-CFO-SBX",
            "environment": "sandbox",
            "authMode": "placeholder",
            "mockMode": True,
            "token": "do-not-store",
            "password": "do-not-store",
            "secret": "do-not-store",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accountId"] == "MOCK-CFO-SBX"
    assert body["environment"] == "sandbox"
    assert body["authMode"] == "placeholder"
    assert body["mockMode"] is True
    assert body["mode"] == "mock"
    assert body["status"] == "configured"
    assert "token" not in body
    assert "password" not in body
    assert "secret" not in body


def test_update_netsuite_config_rejects_non_placeholder_auth_mode() -> None:
    response = client.put(
        "/api/v1/connectors/netsuite/config",
        json={
            "accountId": "MOCK-CFO-SBX",
            "environment": "sandbox",
            "authMode": "token",
            "mockMode": True,
        },
    )

    assert response.status_code == 422


def test_test_netsuite_connection_updates_status_and_writes_audit_log() -> None:
    response = client.post("/api/v1/connectors/netsuite/test")

    assert response.status_code == 200
    body = response.json()
    assert body["connectorId"] == "netsuite"
    assert body["success"] is True
    assert body["status"] == "test_passed"
    assert body["mockMode"] is True
    assert body["mode"] == "mock"
    assert body["baseUrlConfigured"] is False
    assert body["credentialsConfigured"] is False
    assert "No credentials were used or stored" in body["message"]
    assert body["testedAt"]

    config = client.get("/api/v1/connectors/netsuite").json()
    assert config["status"] == "test_passed"
    assert config["lastTestedAt"] == body["testedAt"]

    logs = client.get("/api/v1/audit/logs").json()
    assert len(logs) == 1
    assert logs[0]["detectedIntent"] == "CONNECTOR_TEST"
    assert logs[0]["toolsUsed"] == ["connector.netsuite.test_connection"]
    assert logs[0]["endpointCalled"] == "/api/v1/connectors/netsuite/test"
    assert logs[0]["success"] is True
    assert "token" not in logs[0]
    assert "password" not in logs[0]
    assert "secret" not in logs[0]


def test_sandbox_mode_reports_readiness_without_exposing_secrets(monkeypatch) -> None:
    monkeypatch.setenv("NETSUITE_MODE", "sandbox")
    monkeypatch.setenv("NETSUITE_ACCOUNT_ID", "SANDBOX-123")
    monkeypatch.setenv("NETSUITE_BASE_URL", "https://sandbox.suitetalk.api.netsuite.com")
    monkeypatch.setenv("NETSUITE_CONSUMER_KEY", "do-not-return")
    monkeypatch.setenv("NETSUITE_CONSUMER_SECRET", "do-not-return")
    monkeypatch.setenv("NETSUITE_TOKEN_ID", "do-not-return")
    monkeypatch.setenv("NETSUITE_TOKEN_SECRET", "do-not-return")
    get_settings.cache_clear()
    connector_config_service.clear_for_tests()

    response = client.get("/api/v1/connectors/netsuite")

    assert response.status_code == 200
    body = response.json()
    assert body["accountId"] == "SANDBOX-123"
    assert body["authMode"] == "token_based_auth"
    assert body["mockMode"] is False
    assert body["mode"] == "sandbox"
    assert body["baseUrlConfigured"] is True
    assert body["credentialsConfigured"] is True
    assert "do-not-return" not in str(body)
    assert "secret" not in body


def test_sandbox_connection_test_fails_closed_when_credentials_missing(monkeypatch) -> None:
    monkeypatch.setenv("NETSUITE_MODE", "sandbox")
    monkeypatch.setenv("NETSUITE_ACCOUNT_ID", "SANDBOX-123")
    monkeypatch.setenv("NETSUITE_BASE_URL", "https://sandbox.suitetalk.api.netsuite.com")
    monkeypatch.delenv("NETSUITE_CONSUMER_KEY", raising=False)
    monkeypatch.delenv("NETSUITE_CONSUMER_SECRET", raising=False)
    monkeypatch.delenv("NETSUITE_TOKEN_ID", raising=False)
    monkeypatch.delenv("NETSUITE_TOKEN_SECRET", raising=False)
    get_settings.cache_clear()
    connector_config_service.clear_for_tests()

    response = client.post("/api/v1/connectors/netsuite/test")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["status"] == "test_failed"
    assert body["mode"] == "sandbox"
    assert body["baseUrlConfigured"] is True
    assert body["credentialsConfigured"] is False
    assert "credentials are not fully configured" in body["message"]
    assert "password" not in str(body).lower()
    assert "token_secret" not in str(body).lower()
