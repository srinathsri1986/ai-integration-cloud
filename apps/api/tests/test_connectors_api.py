from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.connector_config_service import connector_config_service


client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()
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
    assert body["status"] == "not_configured"
    assert body["lastTestedAt"] is None
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
