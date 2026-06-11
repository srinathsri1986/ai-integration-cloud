"""Tests for R21b inter-step data passing.

All tests must FAIL before the fix and PASS after.

The bug: every step is called with params={} — Step 2 has no access to
Step 1's output. The fix passes a _context dict to each step containing
all prior steps' results, keyed by step.id.

Two invariants:
  1. Context accumulates across steps within a run.
  2. Context does not bleed between separate flow runs.
"""

from __future__ import annotations

import unittest.mock as mock

from fastapi.testclient import TestClient

from app.main import app
from app.services.audit_service import audit_service
from app.services.flow_service import flow_service
from app.services.mapping_definition_service import mapping_definition_service


client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()
    mapping_definition_service.clear_for_tests()


def _create_and_publish(flow_id: str, steps: list[dict]) -> None:
    resp = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": flow_id,
            "name": f"Context test: {flow_id}",
            "description": "Inter-step context test flow.",
            "sourceConnector": "sap",
            "targetModule": "salesforce_account",
            "status": "draft",
            "triggerType": "manual",
            "steps": steps,
        },
    )
    assert resp.status_code == 200, resp.text
    for action in ("submit_for_approval", "approve", "publish"):
        r = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": action})
        assert r.status_code == 200, r.text


def _run_capturing_params(flow_id: str) -> tuple[dict, list[dict]]:
    """Run a flow with a mock that captures the params each call received."""
    captured: list[dict] = []
    call_n = 0

    def fake_execute(connector_id, tool_id, params, tenant_id=None):
        nonlocal call_n
        call_n += 1
        captured.append({"call": call_n, "tool": tool_id, "params": params})
        return {"connector": connector_id, "tool": tool_id, "mode": "mock",
                "result": {"step_output": f"result_from_{tool_id}"}}

    with mock.patch(
        "app.connectors.registry.ConnectorRegistry.execute_tool",
        side_effect=fake_execute,
    ):
        enqueue = client.post(f"/api/v1/flows/{flow_id}/run")
        assert enqueue.status_code == 202
        body = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()

    return body, captured


# ---------------------------------------------------------------------------
# Test 1: context accumulates across steps
# ---------------------------------------------------------------------------

def test_step2_receives_step1_output_in_context() -> None:
    """Step 2's params must include _context["step-1"] = step 1's result."""
    _create_and_publish("ctx-two-steps", [
        {"id": "step-1", "name": "Step One", "description": ".", "approvedTool": "list_vendors"},
        {"id": "step-2", "name": "Step Two", "description": ".", "approvedTool": "get_cost_center"},
    ])

    body, captured = _run_capturing_params("ctx-two-steps")

    assert body["status"] == "succeeded"
    assert len(captured) == 2

    step1_params = captured[0]["params"]
    step2_params = captured[1]["params"]

    # Step 1 should have empty context (nothing before it)
    assert step1_params.get("_context", {}) == {}

    # Step 2 must see step 1's result in _context
    ctx = step2_params.get("_context", {})
    assert "step-1" in ctx, "_context must contain step-1's result by step 2"
    assert ctx["step-1"]["result"]["step_output"] == "result_from_list_vendors"


# ---------------------------------------------------------------------------
# Test 2: context grows step by step
# ---------------------------------------------------------------------------

def test_context_grows_across_three_steps() -> None:
    """Step 3 sees both step-1 and step-2 in _context."""
    _create_and_publish("ctx-three-steps", [
        {"id": "s1", "name": "S1", "description": ".", "approvedTool": "list_vendors"},
        {"id": "s2", "name": "S2", "description": ".", "approvedTool": "get_cost_center"},
        {"id": "s3", "name": "S3", "description": ".", "approvedTool": "get_gl_balance"},
    ])

    body, captured = _run_capturing_params("ctx-three-steps")

    assert body["status"] == "succeeded"
    assert len(captured) == 3

    ctx_s1 = captured[0]["params"].get("_context", {})
    ctx_s2 = captured[1]["params"].get("_context", {})
    ctx_s3 = captured[2]["params"].get("_context", {})

    assert ctx_s1 == {}                         # nothing before s1
    assert "s1" in ctx_s2                       # s2 sees s1
    assert "s1" not in ctx_s2 or True           # (checked above)
    assert "s1" in ctx_s3 and "s2" in ctx_s3   # s3 sees both


# ---------------------------------------------------------------------------
# Test 3: context does not bleed between runs
# ---------------------------------------------------------------------------

def test_context_does_not_bleed_between_runs() -> None:
    """Two separate runs of the same flow must each start with a fresh context."""
    _create_and_publish("ctx-bleed-check", [
        {"id": "step-1", "name": "S1", "description": ".", "approvedTool": "list_vendors"},
        {"id": "step-2", "name": "S2", "description": ".", "approvedTool": "get_cost_center"},
    ])

    all_captured: list[list[dict]] = []

    for _ in range(2):
        _, captured = _run_capturing_params("ctx-bleed-check")
        all_captured.append(captured)

    # In both runs, step-2 should only see the current run's step-1 result —
    # never results from the previous run polluting its context.
    for run_captured in all_captured:
        ctx = run_captured[1]["params"].get("_context", {})
        assert list(ctx.keys()) == ["step-1"], (
            "step-2 context must contain exactly step-1 from the current run"
        )


# ---------------------------------------------------------------------------
# Test 4: single-step flow context is empty dict
# ---------------------------------------------------------------------------

def test_single_step_receives_empty_context() -> None:
    """A flow with one step should still receive _context={} (not absent)."""
    _create_and_publish("ctx-single-step", [
        {"id": "only-step", "name": "Only", "description": ".", "approvedTool": "list_vendors"},
    ])

    _, captured = _run_capturing_params("ctx-single-step")

    assert len(captured) == 1
    params = captured[0]["params"]
    assert "_context" in params
    assert params["_context"] == {}
