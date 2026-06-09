"""Tests for PATCH /flows/{id}/steps/{step_id} — value persistence.

Guards the post-R20 behaviour: a PATCHed approvedTool value must survive
a subsequent GET and must not affect other steps or the flow lifecycle.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.flow_service import flow_service


client = TestClient(app)

_FLOW_ID = "patch-step-test-flow"


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()


def _create_flow() -> dict:
    resp = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": _FLOW_ID,
            "name": "Patch step test",
            "description": "Flow used to test step patching.",
            "sourceConnector": "sap",
            "targetModule": "salesforce_account",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "step-one",
                    "name": "First step",
                    "description": "Initial step",
                    "approvedTool": "sap.list_vendors",
                },
                {
                    "id": "step-two",
                    "name": "Second step",
                    "description": "Another step",
                    "approvedTool": "salesforce.create_account",
                },
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Core persistence
# ---------------------------------------------------------------------------

def test_patched_tool_survives_get() -> None:
    _create_flow()

    patch_resp = client.patch(
        f"/api/v1/flows/{_FLOW_ID}/steps/step-one",
        json={"approvedTool": "sap.get_cost_center"},
    )
    assert patch_resp.status_code == 200, patch_resp.text

    get_resp = client.get(f"/api/v1/flows/{_FLOW_ID}")
    assert get_resp.status_code == 200
    steps = {s["id"]: s for s in get_resp.json()["steps"]}
    assert steps["step-one"]["approvedTool"] == "sap.get_cost_center"


def test_patching_one_step_does_not_affect_other_steps() -> None:
    _create_flow()

    client.patch(
        f"/api/v1/flows/{_FLOW_ID}/steps/step-one",
        json={"approvedTool": "sap.get_cost_center"},
    )

    get_resp = client.get(f"/api/v1/flows/{_FLOW_ID}")
    steps = {s["id"]: s for s in get_resp.json()["steps"]}
    assert steps["step-two"]["approvedTool"] == "salesforce.create_account"


def test_patching_does_not_change_flow_status() -> None:
    _create_flow()

    client.patch(
        f"/api/v1/flows/{_FLOW_ID}/steps/step-one",
        json={"approvedTool": "sap.get_cost_center"},
    )

    get_resp = client.get(f"/api/v1/flows/{_FLOW_ID}")
    assert get_resp.json()["status"] == "draft"


def test_patching_published_flow_step_persists() -> None:
    """PATCH must work on published flows without requiring a status change."""
    _create_flow()
    client.post(f"/api/v1/flows/{_FLOW_ID}/lifecycle", json={"action": "submit_for_approval"})
    client.post(f"/api/v1/flows/{_FLOW_ID}/lifecycle", json={"action": "approve"})
    client.post(f"/api/v1/flows/{_FLOW_ID}/lifecycle", json={"action": "publish"})

    patch_resp = client.patch(
        f"/api/v1/flows/{_FLOW_ID}/steps/step-one",
        json={"approvedTool": "sap.get_cost_center"},
    )
    assert patch_resp.status_code == 200

    get_resp = client.get(f"/api/v1/flows/{_FLOW_ID}")
    steps = {s["id"]: s for s in get_resp.json()["steps"]}
    assert steps["step-one"]["approvedTool"] == "sap.get_cost_center"
    assert get_resp.json()["status"] == "published"


def test_patch_returns_updated_flow_definition() -> None:
    _create_flow()

    patch_resp = client.patch(
        f"/api/v1/flows/{_FLOW_ID}/steps/step-one",
        json={"approvedTool": "sap.get_cost_center"},
    )
    body = patch_resp.json()

    assert body["flowId"] == _FLOW_ID
    steps = {s["id"]: s for s in body["steps"]}
    assert steps["step-one"]["approvedTool"] == "sap.get_cost_center"


def test_patch_nonexistent_flow_returns_404() -> None:
    resp = client.patch(
        "/api/v1/flows/does-not-exist/steps/step-one",
        json={"approvedTool": "sap.list_vendors"},
    )
    assert resp.status_code == 404


def test_consecutive_patches_each_persist() -> None:
    _create_flow()

    client.patch(f"/api/v1/flows/{_FLOW_ID}/steps/step-one", json={"approvedTool": "sap.get_cost_center"})
    client.patch(f"/api/v1/flows/{_FLOW_ID}/steps/step-one", json={"approvedTool": "sap.get_gl_balance"})

    get_resp = client.get(f"/api/v1/flows/{_FLOW_ID}")
    steps = {s["id"]: s for s in get_resp.json()["steps"]}
    assert steps["step-one"]["approvedTool"] == "sap.get_gl_balance"
