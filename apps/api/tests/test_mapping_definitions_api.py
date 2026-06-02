from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


def _valid_mapping_payload() -> dict:
    return {
        "mappingId": "netsuite-project-to-salesforce-opportunity",
        "name": "NetSuite Project to Salesforce Opportunity",
        "description": "Maps approved project fields into Salesforce opportunity fields.",
        "sourceObjectId": "netsuite-project",
        "targetObjectId": "salesforce-opportunity",
        "status": "draft",
        "mappings": [
            {
                "id": "customer-to-account",
                "sourceField": "customer_name",
                "targetField": "AccountName",
                "transform": "direct",
                "confidence": 0.94,
                "rationale": "Customer names align to the account reference.",
            },
            {
                "id": "budget-to-amount",
                "sourceField": "budget_amount",
                "targetField": "Amount",
                "transform": "direct",
                "confidence": 0.91,
                "rationale": "Budget and amount fields are both finance amounts.",
            },
            {
                "id": "date-to-close",
                "sourceField": "due_date",
                "targetField": "CloseDate",
                "transform": "format_date",
                "confidence": 0.88,
                "rationale": "Date values need target date formatting.",
            },
            {
                "id": "manager-to-owner",
                "sourceField": "account_manager",
                "targetField": "OwnerName",
                "transform": "direct",
                "confidence": 0.84,
                "rationale": "Owner fields represent the responsible person.",
            },
            {
                "id": "project-to-name",
                "sourceField": "project_id",
                "targetField": "Name",
                "transform": "rename",
                "confidence": 0.75,
                "rationale": "Project identifier can seed the opportunity name draft.",
            },
        ],
    }


def test_save_and_list_mapping_definition_writes_audit_log() -> None:
    response = client.post("/api/v1/mappings/definitions", json=_valid_mapping_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["mappingId"] == "netsuite-project-to-salesforce-opportunity"
    assert body["status"] == "draft"
    assert len(body["mappings"]) == 5
    assert body["createdAt"]
    assert body["updatedAt"]

    listed = client.get("/api/v1/mappings/definitions").json()
    assert [mapping["mappingId"] for mapping in listed] == [
        "netsuite-project-to-salesforce-opportunity"
    ]

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "MAPPING_DEFINITION"
    assert logs[0]["question"] == (
        "Mapping definition action: netsuite-project-to-salesforce-opportunity.upsert"
    )
    assert logs[0]["toolsUsed"] == ["mapping.definition.upsert"]


def test_mapping_definition_requires_known_fields_and_required_targets() -> None:
    payload = _valid_mapping_payload()
    payload["mappings"] = [
        {
            "id": "bad",
            "sourceField": "invented_field",
            "targetField": "AccountName",
            "transform": "direct",
        }
    ]

    response = client.post("/api/v1/mappings/definitions", json=payload)

    assert response.status_code == 422
    assert "Unknown source field" in response.json()["detail"]


def test_mapping_lifecycle_requires_human_approval_before_publish() -> None:
    client.post("/api/v1/mappings/definitions", json=_valid_mapping_payload())

    publish_first = client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "publish"},
    )
    assert publish_first.status_code == 409

    submitted = client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "submit_for_approval"},
    ).json()
    assert submitted["mapping"]["status"] == "pending_approval"

    approved = client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "approve"},
    ).json()
    assert approved["mapping"]["status"] == "approved"

    published = client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/lifecycle",
        json={"action": "publish"},
    ).json()
    assert published["mapping"]["status"] == "published"

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["question"] == (
        "Mapping definition action: netsuite-project-to-salesforce-opportunity.publish"
    )
    assert logs[1]["question"] == (
        "Mapping definition action: netsuite-project-to-salesforce-opportunity.approve"
    )
    assert logs[2]["question"] == (
        "Mapping definition action: netsuite-project-to-salesforce-opportunity.submit_for_approval"
    )


def test_mapping_definition_rejects_raw_query_language() -> None:
    payload = _valid_mapping_payload()
    payload["description"] = "Run select * from transaction before mapping."

    response = client.post("/api/v1/mappings/definitions", json=payload)

    assert response.status_code == 422


def test_mapping_simulation_returns_sample_source_and_target_payloads() -> None:
    client.post("/api/v1/mappings/definitions", json=_valid_mapping_payload())

    response = client.post(
        "/api/v1/mappings/definitions/netsuite-project-to-salesforce-opportunity/simulate"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mappingId"] == "netsuite-project-to-salesforce-opportunity"
    assert body["sourcePayload"]["customer_name"] == "Acme Manufacturing"
    assert body["targetPayload"]["AccountName"] == "Acme Manufacturing"
    assert body["targetPayload"]["Amount"] == 420000
    assert body["targetPayload"]["CloseDate"] == "2026-03-31"
    assert body["targetPayload"]["Name"] == "PRJ-1042"
    assert body["warnings"] == []
    assert "direct" in body["transformsApplied"]
    assert "format_date" in body["transformsApplied"]

    logs = client.get("/api/v1/audit/logs").json()
    assert logs[0]["detectedIntent"] == "MAPPING_SIMULATION"
    assert logs[0]["toolsUsed"] == ["mapping.simulate"]
    assert logs[0]["success"] is True


def test_mapping_simulation_returns_404_for_unknown_mapping() -> None:
    response = client.post("/api/v1/mappings/definitions/missing-mapping/simulate")

    assert response.status_code == 404


def test_mapping_simulation_surfaces_required_field_warnings() -> None:
    payload = _valid_mapping_payload()
    payload["mappingId"] = "project-to-rest-customer"
    payload["sourceObjectId"] = "netsuite-project"
    payload["targetObjectId"] = "rest-customer"
    payload["mappings"] = [
        {
            "id": "project-to-external",
            "sourceField": "project_id",
            "targetField": "externalId",
            "transform": "rename",
        },
        {
            "id": "active-constant",
            "sourceField": "project_id",
            "targetField": "isActive",
            "transform": "constant_placeholder",
        },
    ]
    # Persist directly through the repository-facing model path to exercise runtime warnings
    # without weakening save-time required-field validation.
    from app.core.database import SessionLocal
    from app.models.mapping import MappingDefinition
    from app.repositories.mapping_definition_repository import MappingDefinitionRepository

    with SessionLocal() as session:
        MappingDefinitionRepository(session).upsert(
            MappingDefinition(
                mappingId="project-to-rest-customer",
                name="Project to REST Customer",
                description="Partial mapping used to preview runtime warnings.",
                sourceObjectId="netsuite-project",
                targetObjectId="rest-customer",
                status="draft",
                mappings=payload["mappings"],
            )
        )

    response = client.post("/api/v1/mappings/definitions/project-to-rest-customer/simulate")

    assert response.status_code == 200
    body = response.json()
    assert body["targetPayload"]["externalId"] == "PRJ-1042"
    assert body["targetPayload"]["isActive"] == "reviewed_constant_placeholder"
    assert body["warnings"] == ["Required target field displayName was not populated."]
