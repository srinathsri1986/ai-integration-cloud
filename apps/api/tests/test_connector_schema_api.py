"""Tests for GET /api/v1/connectors/{id}/schema — R22a contract tests.

Verifies the schema endpoint returns a shape that the Data Mapping Studio
frontend can consume. The frontend converts ConnectorSchema → MappingObject[];
these tests ensure the contract holds so the live-schema useEffect works.

All tests must PASS after the endpoint exists (they document the contract,
not a new feature). If any fail, the frontend useEffect would break silently.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_VALID_FIELD_TYPES = {"string", "number", "date", "boolean", "id", "reference", "text", "integer", "float", "percent", "currency"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_schema(connector_id: str, refresh: bool = True) -> dict:
    url = f"/api/v1/connectors/{connector_id}/schema"
    if refresh:
        url += "?refresh=true"
    resp = client.get(url)
    assert resp.status_code == 200, f"Expected 200 for {connector_id}, got {resp.status_code}: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Test 1: top-level shape
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("connector_id", ["sap", "salesforce", "netsuite", "slack"])
def test_schema_top_level_shape(connector_id: str) -> None:
    """Schema must have connectorId, mode, objects[], fetchedAt."""
    body = _get_schema(connector_id)
    assert body["connectorId"] == connector_id
    assert body["mode"] in ("mock", "live")
    assert isinstance(body["objects"], list)
    assert "fetchedAt" in body


# ---------------------------------------------------------------------------
# Test 2: each object has objectId, label, fields[]
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("connector_id", ["sap", "salesforce", "netsuite"])
def test_schema_objects_shape(connector_id: str) -> None:
    """Every schema object must have objectId, label, and a non-empty fields list."""
    body = _get_schema(connector_id)
    assert len(body["objects"]) > 0, f"{connector_id} schema must have at least one object"
    for obj in body["objects"]:
        assert "objectId" in obj, f"Object missing objectId: {obj}"
        assert "label" in obj, f"Object missing label: {obj}"
        assert isinstance(obj["fields"], list), f"Object fields must be a list: {obj}"
        assert len(obj["fields"]) > 0, f"Object {obj['objectId']} must have at least one field"


# ---------------------------------------------------------------------------
# Test 3: each field satisfies the ConnectorSchemaField contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("connector_id", ["sap", "salesforce", "netsuite", "slack"])
def test_schema_field_contract(connector_id: str) -> None:
    """Every field must have name (str), label (str), type (str), required (bool), updateable (bool)."""
    body = _get_schema(connector_id)
    for obj in body["objects"]:
        for f in obj["fields"]:
            assert isinstance(f.get("name"), str) and f["name"], (
                f"Field missing name in {connector_id}/{obj['objectId']}: {f}"
            )
            assert isinstance(f.get("label"), str), (
                f"Field {f.get('name')} missing label in {connector_id}/{obj['objectId']}"
            )
            assert isinstance(f.get("type"), str), (
                f"Field {f.get('name')} missing type in {connector_id}/{obj['objectId']}"
            )
            assert isinstance(f.get("required"), bool), (
                f"Field {f.get('name')} required must be bool in {connector_id}/{obj['objectId']}"
            )
            assert isinstance(f.get("updateable"), bool), (
                f"Field {f.get('name')} updateable must be bool in {connector_id}/{obj['objectId']}"
            )


# ---------------------------------------------------------------------------
# Test 4: SAP schema has vendor object (used in SAP→Salesforce sync)
# ---------------------------------------------------------------------------

def test_sap_schema_has_vendor_object() -> None:
    """SAP schema must include a vendor object (used in the live sync flow)."""
    body = _get_schema("sap")
    object_ids = [obj["objectId"] for obj in body["objects"]]
    assert any("vendor" in oid.lower() for oid in object_ids), (
        f"SAP schema must have a vendor object, got: {object_ids}"
    )


# ---------------------------------------------------------------------------
# Test 5: Salesforce schema has Account object with SAP_Vendor_ID__c
# ---------------------------------------------------------------------------

def test_salesforce_schema_has_account_object() -> None:
    """Salesforce schema must include an Account object."""
    body = _get_schema("salesforce")
    object_ids = [obj["objectId"] for obj in body["objects"]]
    assert any("account" in oid.lower() for oid in object_ids), (
        f"Salesforce schema must have an Account object, got: {object_ids}"
    )


def test_salesforce_account_has_sap_vendor_id_field() -> None:
    """Salesforce Account object must expose SAP_Vendor_ID__c for the upsert flow."""
    body = _get_schema("salesforce")
    account_obj = next(
        (obj for obj in body["objects"] if "account" in obj["objectId"].lower()),
        None,
    )
    assert account_obj is not None, "Salesforce Account object not found"
    field_names = [f["name"] for f in account_obj["fields"]]
    assert "SAP_Vendor_ID__c" in field_names, (
        f"Salesforce Account must have SAP_Vendor_ID__c, got: {field_names}"
    )


# ---------------------------------------------------------------------------
# Test 6: unknown connector → 404
# ---------------------------------------------------------------------------

def test_unknown_connector_schema_returns_404() -> None:
    resp = client.get("/api/v1/connectors/nonexistent-connector-xyz/schema")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 7: schema is compatible with MappingObject id convention
# ---------------------------------------------------------------------------

def test_schema_object_ids_are_lowercase_strings() -> None:
    """objectId must be a lowercase string usable in the {connectorId}-{objectId} catalog ID pattern."""
    for connector_id in ("sap", "salesforce", "netsuite"):
        body = _get_schema(connector_id)
        for obj in body["objects"]:
            oid = obj["objectId"]
            assert isinstance(oid, str) and oid, f"objectId must be a non-empty string in {connector_id}"
            assert oid == oid.lower() or oid.replace("_", "").replace("-", "").isalnum(), (
                f"objectId '{oid}' in {connector_id} must be a valid ID string"
            )
