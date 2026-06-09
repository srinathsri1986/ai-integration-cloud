"""Tests for the mapping-definition branch inside _execute_flow_sync().

Guards the post-R20 flow-engine behaviour: when a published flow has a
mappingDefinitionId attached, the engine must:
  1. Populate data["mappingSimulation"] with the catalog-sample preview.
  2. Populate data["mappingDefinitionId"].
  3. Record a "mapping-simulation" step in the execution timeline.
  4. Set inspection.hasSourcePayload / hasTargetPayload = True.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.flow_service import flow_service
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FLOW_ID = "flow-mapping-branch-test"
_MAPPING_ID = "netsuite-project-to-salesforce-opportunity"


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


def _create_and_publish_mapping() -> None:
    client.post(
        "/api/v1/mappings/definitions",
        json={
            "mappingId": _MAPPING_ID,
            "name": "NetSuite Project to Salesforce Opportunity",
            "description": "Maps approved project fields into Salesforce opportunity fields.",
            "sourceObjectId": "netsuite-project",
            "targetObjectId": "salesforce-opportunity",
            "status": "draft",
            "mappings": [
                {"id": "m1", "sourceField": "project_id",    "targetField": "Name",        "transform": "direct"},
                {"id": "m2", "sourceField": "customer_name", "targetField": "AccountName",  "transform": "direct"},
                {"id": "m3", "sourceField": "budget_amount", "targetField": "Amount",       "transform": "direct"},
                {"id": "m4", "sourceField": "due_date",      "targetField": "CloseDate",    "transform": "format_date"},
            ],
        },
    )
    for action in ("submit_for_approval", "approve", "publish"):
        client.post(f"/api/v1/mappings/definitions/{_MAPPING_ID}/lifecycle", json={"action": action})


def _create_and_publish_flow() -> None:
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": _FLOW_ID,
            "name": "Flow mapping branch test",
            "description": "Test that the mapping branch runs correctly.",
            "sourceConnector": "netsuite",
            "targetModule": "salesforce_opportunity",
            "status": "draft",
            "triggerType": "manual",
            "mappingDefinitionId": _MAPPING_ID,
            "steps": [
                {
                    "id": "read",
                    "name": "Load CFO data",
                    "description": "Pull summary.",
                    "approvedTool": "cfo.dashboard_summary",
                }
            ],
        },
    )
    for action in ("submit_for_approval", "approve", "publish"):
        client.post(f"/api/v1/flows/{_FLOW_ID}/lifecycle", json={"action": action})


def _run_and_wait(flow_id: str) -> dict:
    run_resp = client.post(f"/api/v1/flows/{flow_id}/run")
    assert run_resp.status_code == 202
    request_id = run_resp.json()["requestId"]
    result = client.get(f"/api/v1/flows/runs/{request_id}")
    return result.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_mapping_simulation_key_present_in_run_data() -> None:
    _create_and_publish_mapping()
    _create_and_publish_flow()

    body = _run_and_wait(_FLOW_ID)

    assert body["status"] == "succeeded"
    assert "mappingSimulation" in body["data"]


def test_mapping_simulation_has_source_and_target_payload() -> None:
    _create_and_publish_mapping()
    _create_and_publish_flow()

    body = _run_and_wait(_FLOW_ID)
    sim = body["data"]["mappingSimulation"]

    assert "sourcePayload" in sim
    assert "targetPayload" in sim


def test_mapping_simulation_target_payload_contains_sample_values() -> None:
    _create_and_publish_mapping()
    _create_and_publish_flow()

    body = _run_and_wait(_FLOW_ID)
    target = body["data"]["mappingSimulation"]["targetPayload"]

    assert target.get("AccountName") == "Acme Manufacturing"
    assert target.get("Name") == "PRJ-1042"


def test_mapping_definition_id_recorded_in_run_data() -> None:
    _create_and_publish_mapping()
    _create_and_publish_flow()

    body = _run_and_wait(_FLOW_ID)

    assert body["data"]["mappingDefinitionId"] == _MAPPING_ID


def test_mapping_simulation_step_in_timeline() -> None:
    _create_and_publish_mapping()
    _create_and_publish_flow()

    body = _run_and_wait(_FLOW_ID)
    step_ids = [s["id"] for s in body["executionTimeline"]]

    assert "mapping-simulation" in step_ids


def test_inspection_has_source_and_target_payload_flags() -> None:
    _create_and_publish_mapping()
    _create_and_publish_flow()

    body = _run_and_wait(_FLOW_ID)

    assert body["inspection"]["hasSourcePayload"] is True
    assert body["inspection"]["hasTargetPayload"] is True


def test_flow_without_mapping_does_not_set_mapping_simulation() -> None:
    """Sanity: a flow with no mappingDefinitionId must not have mappingSimulation."""
    plain_id = "flow-no-mapping"
    client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": plain_id,
            "name": "No mapping flow",
            "description": "No mapping attached.",
            "sourceConnector": "netsuite",
            "targetModule": "salesforce_account",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {"id": "s1", "name": "Step", "description": ".", "approvedTool": "cfo.dashboard_summary"}
            ],
        },
    )
    for action in ("submit_for_approval", "approve", "publish"):
        client.post(f"/api/v1/flows/{plain_id}/lifecycle", json={"action": action})

    body = _run_and_wait(plain_id)
    assert "mappingSimulation" not in body["data"]
