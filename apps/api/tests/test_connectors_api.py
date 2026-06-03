from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.services.audit_service import audit_service
from app.services.connector_config_service import connector_config_service
from app.services.mapping_catalog import clear_promoted_mapping_objects_for_tests
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


def setup_function() -> None:
    get_settings.cache_clear()
    audit_service.clear_for_tests()
    connector_config_service.clear_for_tests()
    clear_promoted_mapping_objects_for_tests()
    mapping_definition_service.clear_for_tests()


def teardown_function() -> None:
    get_settings.cache_clear()
    connector_config_service.clear_for_tests()
    clear_promoted_mapping_objects_for_tests()
    mapping_definition_service.clear_for_tests()


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
        },
        {
            "id": "rest-api",
            "name": "REST API",
            "status": "not_configured",
            "mockMode": True,
            "mode": "mock",
            "lastTestedAt": None,
        },
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


def test_get_rest_api_config_returns_governed_mock_config() -> None:
    response = client.get("/api/v1/connectors/rest-api")

    assert response.status_code == 200
    body = response.json()
    assert body["connectorId"] == "rest-api"
    assert body["displayName"] == "Generic REST API"
    assert body["baseUrlPlaceholder"] == "https://api.example.com"
    assert body["authMode"] == "placeholder"
    assert body["mockMode"] is True
    assert body["mode"] == "mock"
    assert body["status"] == "not_configured"
    assert body["baseUrlConfigured"] is False
    assert body["credentialsConfigured"] is False
    assert body["approvedObjects"] == ["customer", "invoice", "opportunity"]
    assert body["approvedActions"] == [
        "read_sample",
        "validate_payload",
        "simulate_post_placeholder",
    ]
    assert "password" not in body
    assert "token" not in body
    assert "secret" not in body


def test_update_rest_api_config_stores_placeholders_only() -> None:
    response = client.put(
        "/api/v1/connectors/rest-api/config",
        json={
            "displayName": "Customer REST Gateway",
            "baseUrlPlaceholder": "https://customer-api.example.com",
            "authMode": "placeholder",
            "mockMode": True,
            "apiKey": "do-not-store",
            "bearerToken": "do-not-store",
            "secret": "do-not-store",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["displayName"] == "Customer REST Gateway"
    assert body["baseUrlPlaceholder"] == "https://customer-api.example.com"
    assert body["authMode"] == "placeholder"
    assert body["mockMode"] is True
    assert body["mode"] == "mock"
    assert body["status"] == "configured"
    assert "apiKey" not in body
    assert "bearerToken" not in body
    assert "secret" not in body


def test_rest_api_config_rejects_non_placeholder_auth_mode() -> None:
    response = client.put(
        "/api/v1/connectors/rest-api/config",
        json={
            "displayName": "Customer REST Gateway",
            "baseUrlPlaceholder": "https://customer-api.example.com",
            "authMode": "api_key",
            "mockMode": True,
        },
    )

    assert response.status_code == 422


def test_list_rest_api_objects_returns_approved_schema_catalog() -> None:
    response = client.get("/api/v1/connectors/rest-api/objects")

    assert response.status_code == 200
    body = response.json()
    assert [item["objectId"] for item in body] == ["customer", "invoice", "opportunity"]
    assert body[0]["fields"][0] == {
        "name": "externalId",
        "label": "External ID",
        "type": "string",
        "required": True,
    }


def test_discover_rest_api_schema_infers_safe_top_level_fields() -> None:
    response = client.post(
        "/api/v1/connectors/rest-api/discover-schema",
        json={
            "objectLabel": "Customer Event",
            "samplePayload": {
                "externalId": "CUST-100",
                "amount": 2500.75,
                "invoiceDate": "2026-06-02",
                "isActive": True,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["connectorId"] == "rest-api"
    assert body["objectId"] == "rest-discovered-customer-event"
    assert body["objectLabel"] == "Customer Event"
    assert body["mode"] == "schema_discovery"
    assert body["generatedFromSample"] is True
    assert body["executable"] is False
    assert body["warnings"] == []
    assert body["fields"] == [
        {
            "name": "externalId",
            "label": "External Id",
            "type": "string",
            "required": True,
            "sample": "CUST-100",
        },
        {
            "name": "amount",
            "label": "Amount",
            "type": "number",
            "required": True,
            "sample": 2500.75,
        },
        {
            "name": "invoiceDate",
            "label": "Invoice Date",
            "type": "date",
            "required": True,
            "sample": "2026-06-02",
        },
        {
            "name": "isActive",
            "label": "Is Active",
            "type": "boolean",
            "required": True,
            "sample": True,
        },
    ]


def test_discover_rest_api_schema_skips_secret_and_nested_fields() -> None:
    response = client.post(
        "/api/v1/connectors/rest-api/discover-schema",
        json={
            "objectLabel": "Payment Event",
            "samplePayload": {
                "customerId": "CUST-100",
                "apiKey": "do-not-discover",
                "nested": {"raw": "unsupported"},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [field["name"] for field in body["fields"]] == ["customerId"]
    assert len(body["warnings"]) == 2
    assert "apiKey was skipped" in body["warnings"][0]
    assert "nested was skipped" in body["warnings"][1]
    assert "do-not-discover" not in str(body)


def test_discover_rest_api_schema_rejects_empty_payload() -> None:
    response = client.post(
        "/api/v1/connectors/rest-api/discover-schema",
        json={"objectLabel": "Empty Event", "samplePayload": {}},
    )

    assert response.status_code == 422


def test_promote_rest_api_schema_allows_governed_mapping_save_and_simulation() -> None:
    discovery = client.post(
        "/api/v1/connectors/rest-api/discover-schema",
        json={
            "objectLabel": "Customer Event",
            "samplePayload": {
                "externalId": "CUST-100",
                "displayName": "Acme Manufacturing",
                "amount": 2500.75,
                "invoiceDate": "2026-06-02",
            },
        },
    ).json()

    promoted = client.post(
        "/api/v1/connectors/rest-api/promote-schema",
        json={
            "objectId": discovery["objectId"],
            "objectLabel": discovery["objectLabel"],
            "fields": discovery["fields"],
        },
    )

    assert promoted.status_code == 200
    promoted_body = promoted.json()
    assert promoted_body["connectorId"] == "rest-api"
    assert promoted_body["promoted"] is True
    assert promoted_body["objectId"] == "rest-governed-customer-event"
    assert promoted_body["mappingObject"]["systemId"] == "rest-api"
    assert promoted_body["mappingObject"]["fields"][0]["name"] == "externalId"

    mapping_response = client.post(
        "/api/v1/mappings/definitions",
        json={
            "mappingId": "rest-customer-event-to-salesforce-opportunity",
            "name": "REST Customer Event to Salesforce Opportunity",
            "description": "Maps promoted REST customer event fields into Salesforce opportunity fields.",
            "sourceObjectId": "rest-governed-customer-event",
            "targetObjectId": "salesforce-opportunity",
            "status": "draft",
            "mappings": [
                {
                    "id": "display-to-name",
                    "sourceField": "displayName",
                    "targetField": "Name",
                    "transform": "direct",
                },
                {
                    "id": "external-to-account",
                    "sourceField": "externalId",
                    "targetField": "AccountName",
                    "transform": "rename",
                },
                {
                    "id": "amount-to-amount",
                    "sourceField": "amount",
                    "targetField": "Amount",
                    "transform": "direct",
                },
                {
                    "id": "date-to-close",
                    "sourceField": "invoiceDate",
                    "targetField": "CloseDate",
                    "transform": "format_date",
                },
            ],
        },
    )

    assert mapping_response.status_code == 200

    simulation = client.post(
        "/api/v1/mappings/definitions/rest-customer-event-to-salesforce-opportunity/simulate"
    )
    assert simulation.status_code == 200
    simulation_body = simulation.json()
    assert simulation_body["sourcePayload"]["externalId"] == "CUST-100"
    assert simulation_body["targetPayload"]["Name"] == "Acme Manufacturing"
    assert simulation_body["targetPayload"]["Amount"] == 2500.75

    logs = client.get("/api/v1/audit/logs").json()
    assert any(log["toolsUsed"] == ["connector.rest-api.schema_promotion"] for log in logs)


def test_promote_rest_api_schema_skips_secret_like_fields() -> None:
    response = client.post(
        "/api/v1/connectors/rest-api/promote-schema",
        json={
            "objectId": "rest-discovered-payment-event",
            "objectLabel": "Payment Event",
            "fields": [
                {
                    "name": "apiKey",
                    "label": "Api Key",
                    "type": "string",
                    "required": True,
                    "sample": "do-not-store",
                },
                {
                    "name": "customerId",
                    "label": "Customer Id",
                    "type": "string",
                    "required": True,
                    "sample": "CUST-100",
                },
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [field["name"] for field in body["mappingObject"]["fields"]] == ["customerId"]
    assert body["warnings"] == ["apiKey was skipped because it looks like a secret or credential field."]
    assert "do-not-store" not in str(body)


def test_test_rest_api_connection_updates_status_and_writes_audit_log() -> None:
    response = client.post("/api/v1/connectors/rest-api/test")

    assert response.status_code == 200
    body = response.json()
    assert body["connectorId"] == "rest-api"
    assert body["success"] is True
    assert body["status"] == "test_passed"
    assert body["mockMode"] is True
    assert body["mode"] == "mock"
    assert body["baseUrlConfigured"] is False
    assert body["credentialsConfigured"] is False
    assert body["approvedObjects"] == ["customer", "invoice", "opportunity"]
    assert "No outbound HTTP request was made" in body["message"]
    assert "No credentials were used or stored" in body["message"]

    config = client.get("/api/v1/connectors/rest-api").json()
    assert config["status"] == "test_passed"
    assert config["lastTestedAt"] == body["testedAt"]

    logs = client.get("/api/v1/audit/logs").json()
    assert len(logs) == 1
    assert logs[0]["detectedIntent"] == "CONNECTOR_TEST"
    assert logs[0]["toolsUsed"] == ["connector.rest-api.test_connection"]
    assert logs[0]["endpointCalled"] == "/api/v1/connectors/rest-api/test"
    assert logs[0]["success"] is True
    assert "apiKey" not in logs[0]
    assert "password" not in logs[0]
    assert "secret" not in logs[0]


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
