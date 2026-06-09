"""Tests for mapping_definition_service.apply_mapping() — live payload path.

Guards the post-R20 behaviour: apply_mapping takes a real dict from a
connector step and returns (target_payload, warnings). This is distinct
from simulate_mapping which uses static catalog sample data.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAPPING_ID = "sap-vendor-to-salesforce-account-live"

_MAPPING_PAYLOAD = {
    "mappingId": _MAPPING_ID,
    "name": "SAP Vendor to Salesforce Account (live)",
    "description": "Maps SAP vendor ID and name to Salesforce Account fields.",
    "sourceObjectId": "sap-vendor",
    "targetObjectId": "salesforce-account",
    "status": "draft",
    "mappings": [
        {"id": "id-to-ext",    "sourceField": "id",   "targetField": "SAP_Vendor_ID__c", "transform": "direct"},
        {"id": "name-to-name", "sourceField": "name",  "targetField": "Name",             "transform": "direct"},
    ],
}


def _publish_mapping() -> None:
    resp = client.post("/api/v1/mappings/definitions", json=_MAPPING_PAYLOAD)
    assert resp.status_code == 200, resp.text
    for action in ("submit_for_approval", "approve", "publish"):
        r = client.post(f"/api/v1/mappings/definitions/{_MAPPING_ID}/lifecycle", json={"action": action})
        assert r.status_code == 200, r.text


def setup_function() -> None:
    audit_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_apply_mapping_maps_all_present_fields() -> None:
    _publish_mapping()
    payload = {"id": "V-001", "name": "Acme Corp"}

    target, warnings = mapping_definition_service.apply_mapping(_MAPPING_ID, payload)

    assert target["SAP_Vendor_ID__c"] == "V-001"
    assert target["Name"] == "Acme Corp"
    assert warnings == []


def test_apply_mapping_warns_on_missing_source_field() -> None:
    _publish_mapping()
    payload = {"id": "V-002"}  # "name" is absent

    target, warnings = mapping_definition_service.apply_mapping(_MAPPING_ID, payload)

    assert target["SAP_Vendor_ID__c"] == "V-002"
    assert "Name" not in target
    assert any("name" in w for w in warnings)


def test_apply_mapping_empty_source_produces_all_warnings() -> None:
    _publish_mapping()

    target, warnings = mapping_definition_service.apply_mapping(_MAPPING_ID, {})

    assert target == {}
    assert len(warnings) == 2  # one per mapping row


def test_apply_mapping_transform_direct_preserves_value() -> None:
    _publish_mapping()
    payload = {"id": "V-003", "name": "Numeric ID Vendor"}

    target, _ = mapping_definition_service.apply_mapping(_MAPPING_ID, payload)

    assert target["SAP_Vendor_ID__c"] == "V-003"


def test_apply_mapping_extra_source_fields_are_ignored() -> None:
    _publish_mapping()
    payload = {"id": "V-004", "name": "Extra Corp", "irrelevant_field": "noise", "another": 123}

    target, warnings = mapping_definition_service.apply_mapping(_MAPPING_ID, payload)

    assert "irrelevant_field" not in target
    assert "another" not in target
    assert warnings == []
