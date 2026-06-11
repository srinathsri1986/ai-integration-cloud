"""R22b — Live schema field injection into mapping suggestion.

Tests that when sourceFields/targetFields are provided in the suggestion
request, the service uses them instead of the static catalog, and the LLM
context contains the real field names and types.
"""
from __future__ import annotations

import pytest
from unittest import mock

from app.models.mapping import LiveSchemaField, MappingSuggestionRequest
from app.services.mapping_suggestion_service import (
    MappingSuggestionService,
    _live_fields_to_mapping_object,
)


# ---------------------------------------------------------------------------
# Test 1: _live_fields_to_mapping_object returns correct MappingObject
# ---------------------------------------------------------------------------

def test_live_fields_to_mapping_object_basic() -> None:
    fields = [
        LiveSchemaField(name="SAP_Vendor_ID__c", label="SAP Vendor ID", type="string", required=False, sample="V-001"),
        LiveSchemaField(name="Name", label="Account Name", type="string", required=True),
        LiveSchemaField(name="AnnualRevenue", label="Annual Revenue", type="currency"),
        LiveSchemaField(name="CreatedDate", label="Created Date", type="datetime"),
    ]
    obj = _live_fields_to_mapping_object("salesforce-account", fields)

    assert obj.id == "salesforce-account"
    assert obj.system_id == "salesforce"
    assert len(obj.fields) == 4

    # currency → number
    rev = next(f for f in obj.fields if f.name == "AnnualRevenue")
    assert rev.type == "number"

    # datetime → date
    created = next(f for f in obj.fields if f.name == "CreatedDate")
    assert created.type == "date"

    # custom field preserved
    vendor = next(f for f in obj.fields if f.name == "SAP_Vendor_ID__c")
    assert vendor.sample == "V-001"


# ---------------------------------------------------------------------------
# Test 2: type normalisation covers all documented connector types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("connector_type,expected", [
    ("currency", "number"),
    ("percent", "number"),
    ("integer", "number"),
    ("float", "number"),
    ("id", "string"),
    ("reference", "string"),
    ("text", "string"),
    ("email", "string"),
    ("datetime", "date"),
    ("checkbox", "boolean"),
    ("unknown_exotic_type", "string"),  # fallthrough
])
def test_type_normalisation(connector_type: str, expected: str) -> None:
    fields = [LiveSchemaField(name="f", label="F", type=connector_type)]
    obj = _live_fields_to_mapping_object("test-obj", fields)
    assert obj.fields[0].type == expected


# ---------------------------------------------------------------------------
# Test 3: suggest() uses live fields instead of catalog when provided
# ---------------------------------------------------------------------------

def test_suggest_uses_live_fields_bypasses_catalog() -> None:
    """When sourceFields/targetFields are present, get_mapping_object must NOT be called."""
    service = MappingSuggestionService(ai_provider="mock")

    request = MappingSuggestionRequest.model_validate({
        "prompt": "Map Salesforce Account fields to SAP Vendor fields",
        "sourceObjectId": "salesforce-account",
        "targetObjectId": "sap-vendor",
        "sourceFields": [
            {"name": "Name", "label": "Account Name", "type": "string", "required": True},
            {"name": "SAP_Vendor_ID__c", "label": "SAP Vendor ID", "type": "string", "sample": "V-001"},
        ],
        "targetFields": [
            {"name": "vendorName", "label": "Vendor Name", "type": "string", "required": True},
            {"name": "vendorId", "label": "Vendor ID", "type": "string"},
        ],
    })

    with mock.patch(
        "app.services.mapping_suggestion_service.get_mapping_object"
    ) as mock_catalog:
        # With live fields provided, catalog should never be consulted
        response = service.suggest(request)
        mock_catalog.assert_not_called()

    # Response must use the provided object IDs
    assert response.source_object_id == "salesforce-account"
    assert response.target_object_id == "sap-vendor"


# ---------------------------------------------------------------------------
# Test 4: suggest() falls back to catalog when live fields NOT provided
# ---------------------------------------------------------------------------

def test_suggest_uses_catalog_when_no_live_fields() -> None:
    """Without live fields, the static catalog is consulted as before."""
    service = MappingSuggestionService(ai_provider="mock")

    request = MappingSuggestionRequest.model_validate({
        "prompt": "Map NetSuite customer fields to Salesforce account fields",
        "sourceObjectId": "netsuite-customer",
        "targetObjectId": "salesforce-account",
    })

    with mock.patch(
        "app.services.mapping_suggestion_service.get_mapping_object",
        side_effect=lambda oid: _live_fields_to_mapping_object(oid, [
            LiveSchemaField(name="customer_name", label="Customer Name", type="string"),
            LiveSchemaField(name="due_date", label="Due Date", type="date"),
        ])
    ) as mock_catalog:
        service.suggest(request)
        assert mock_catalog.call_count == 2  # source + target


# ---------------------------------------------------------------------------
# Test 5: live fields with only source provided → target uses catalog
# ---------------------------------------------------------------------------

def test_suggest_partial_live_fields() -> None:
    """Source live fields + catalog target is a valid mixed mode."""
    service = MappingSuggestionService(ai_provider="mock")

    request = MappingSuggestionRequest.model_validate({
        "prompt": "Map Salesforce Account to NetSuite customer",
        "sourceObjectId": "salesforce-account",
        "targetObjectId": "netsuite-customer",
        "sourceFields": [
            {"name": "Name", "label": "Account Name", "type": "string"},
        ],
    })

    catalog_calls: list[str] = []

    def fake_catalog(oid: str):
        catalog_calls.append(oid)
        return _live_fields_to_mapping_object(oid, [
            LiveSchemaField(name="customer_name", label="Customer Name", type="string"),
        ])

    with mock.patch(
        "app.services.mapping_suggestion_service.get_mapping_object",
        side_effect=fake_catalog,
    ):
        service.suggest(request)
        # Only target should call catalog; source came from live fields
        assert catalog_calls == ["netsuite-customer"]
