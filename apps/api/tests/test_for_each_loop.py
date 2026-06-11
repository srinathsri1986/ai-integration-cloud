"""Tests for R21a For Each loop — bulk mapping + write in flow_service.

All four tests must FAIL before the fix and PASS after.

The bug: when step-1 returns a list (e.g. 50 SAP vendors), only items[0]
was processed. The fix replaces that single-record path with a loop that
maps and writes every item.
"""

from __future__ import annotations

import unittest.mock as mock

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.flow_service import flow_service
from app.services.mapping_definition_service import mapping_definition_service

client = TestClient(app)

_FLOW_ID = "for-each-test-flow"
_MAPPING_ID = "sap-vendor-to-salesforce-account-foreach"


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


def _publish_mapping() -> None:
    resp = client.post(
        "/api/v1/mappings/definitions",
        json={
            "mappingId": _MAPPING_ID,
            "name": "SAP Vendor to Salesforce Account (for-each)",
            "description": "Bulk sync of SAP vendors to Salesforce Accounts.",
            "sourceObjectId": "sap-vendor",
            "targetObjectId": "salesforce-account",
            "status": "draft",
            "mappings": [
                {"id": "m1", "sourceField": "id",   "targetField": "SAP_Vendor_ID__c", "transform": "direct"},
                {"id": "m2", "sourceField": "name", "targetField": "Name",             "transform": "direct"},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    for action in ("submit_for_approval", "approve", "publish"):
        r = client.post(f"/api/v1/mappings/definitions/{_MAPPING_ID}/lifecycle", json={"action": action})
        assert r.status_code == 200, r.text


def _create_and_publish_flow() -> None:
    resp = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": _FLOW_ID,
            "name": "For Each test flow",
            "description": "Tests bulk processing of list results.",
            "sourceConnector": "sap",
            "targetModule": "salesforce_account",
            "status": "draft",
            "triggerType": "manual",
            "mappingDefinitionId": _MAPPING_ID,
            "steps": [
                {
                    "id": "read",
                    "name": "List vendors",
                    "description": "Fetch all SAP vendors.",
                    "approvedTool": "list_vendors",
                }
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    for action in ("submit_for_approval", "approve", "publish"):
        r = client.post(f"/api/v1/flows/{_FLOW_ID}/lifecycle", json={"action": action})
        assert r.status_code == 200, r.text


def _make_list_result(n: int) -> dict:
    """Build a connector result dict with n vendor records, as list_vendors returns."""
    return {
        "connector": "sap",
        "tool": "list_vendors",
        "mode": "mock",
        "result": {
            "items": [{"id": f"V-{i:03d}", "name": f"Vendor {i}"} for i in range(1, n + 1)],
            "count": n,
        },
    }


def _run_with_mocked_step(step_result: dict, write_side_effect=None) -> dict:
    """Run the flow with a mocked step-1 result and optionally mocked write calls."""
    _publish_mapping()
    _create_and_publish_flow()

    write_mock = mock.MagicMock(
        side_effect=write_side_effect,
        return_value={"connector": "salesforce", "tool": "create_account", "mode": "mock", "result": {"upserted": True}},
    )

    with mock.patch(
        "app.connectors.registry.ConnectorRegistry.execute_tool",
        side_effect=lambda connector_id, tool_id, params, tenant_id=None: (
            step_result if tool_id == "list_vendors" else write_mock(connector_id, tool_id, params, tenant_id=tenant_id)
        ),
    ):
        enqueue = client.post(f"/api/v1/flows/{_FLOW_ID}/run")
        assert enqueue.status_code == 202
        body = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()

    return body, write_mock


# ---------------------------------------------------------------------------
# Test 1: all items processed
# ---------------------------------------------------------------------------

def test_for_each_processes_all_items() -> None:
    """10 items in → execute_tool (write) called exactly 10 times."""
    body, write_mock = _run_with_mocked_step(_make_list_result(10))

    assert body["status"] == "succeeded"
    bulk = body["data"]["targetWriteResult"]
    assert bulk["mode"] == "bulk"
    assert bulk["total"] == 10
    assert bulk["succeeded"] == 10
    assert bulk["failed"] == 0
    assert write_mock.call_count == 10


# ---------------------------------------------------------------------------
# Test 2: partial failure — loop continues, failed count tracked
# ---------------------------------------------------------------------------

def test_for_each_partial_failure() -> None:
    """Item 3 raises → failed:1, succeeded:9, loop continues through all items."""
    call_count = 0

    def write_side_effect(connector_id, tool_id, params, tenant_id=None):
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise RuntimeError("Simulated write failure on item 3")
        return {"connector": "salesforce", "tool": tool_id, "mode": "mock", "result": {"upserted": True}}

    body, _ = _run_with_mocked_step(_make_list_result(10), write_side_effect=write_side_effect)

    bulk = body["data"]["targetWriteResult"]
    assert bulk["total"] == 10
    assert bulk["failed"] == 1
    assert bulk["succeeded"] == 9
    # Run still succeeds overall (partial failure doesn't abort)
    assert body["status"] == "succeeded"


# ---------------------------------------------------------------------------
# Test 3: bulk result shape
# ---------------------------------------------------------------------------

def test_bulk_write_result_shape() -> None:
    """targetWriteResult has {mode, total, succeeded, failed, items[]}."""
    body, _ = _run_with_mocked_step(_make_list_result(3))

    bulk = body["data"]["targetWriteResult"]
    assert bulk["mode"] == "bulk"
    assert "total" in bulk
    assert "succeeded" in bulk
    assert "failed" in bulk
    assert isinstance(bulk["items"], list)
    assert len(bulk["items"]) == 3

    # Each item entry has source + status
    for entry in bulk["items"]:
        assert "source" in entry
        assert "status" in entry


# ---------------------------------------------------------------------------
# Test 4: single-record path unchanged
# ---------------------------------------------------------------------------

def test_single_record_path_unchanged() -> None:
    """When step-1 returns a plain dict (not a list), the single-write path runs."""
    _publish_mapping()
    _create_and_publish_flow()

    single_result = {
        "connector": "sap",
        "tool": "list_vendors",
        "mode": "mock",
        "result": {"id": "V-001", "name": "Solo Vendor"},  # no "items" key
    }

    write_mock = mock.MagicMock(
        return_value={"connector": "salesforce", "tool": "create_account", "mode": "mock",
                      "result": {"upserted": True}},
    )

    with mock.patch(
        "app.connectors.registry.ConnectorRegistry.execute_tool",
        side_effect=lambda connector_id, tool_id, params, tenant_id=None: (
            single_result if tool_id == "list_vendors" else write_mock(connector_id, tool_id, params, tenant_id=tenant_id)
        ),
    ):
        enqueue = client.post(f"/api/v1/flows/{_FLOW_ID}/run")
        assert enqueue.status_code == 202
        body = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()

    assert body["status"] == "succeeded"
    # Single path: targetWriteResult is NOT a bulk dict
    write_result = body["data"].get("targetWriteResult", {})
    assert write_result.get("mode") != "bulk", "Single-record path must not produce a bulk result"
    write_mock.assert_called_once()
