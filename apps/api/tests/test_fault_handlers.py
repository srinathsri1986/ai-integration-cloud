"""Tests for R21c fault handlers + auto-timeout.

All tests must FAIL before the fix and PASS after.

Three behaviours under test:
  1. on_error: "skip"  — failing step is skipped, next steps continue.
  2. on_error: "retry" — failing step is retried up to max_retries times.
  3. on_error: "stop"  — (default) failing step stops the run (existing behaviour).
  4. Stuck runs (running > 15 min) are marked timed_out by the Beat task.
"""

from __future__ import annotations

import unittest.mock as mock
from datetime import UTC, datetime, timedelta

import pytest
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


def _make_flow(flow_id: str, steps: list[dict]) -> None:
    resp = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": flow_id,
            "name": f"Fault handler test: {flow_id}",
            "description": "Tests fault handling policies on steps.",
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


def _run_with_failing_step(flow_id: str, fail_on_tool: str, call_log: list) -> dict:
    """Run a flow where the given tool always raises RuntimeError."""
    def fake_execute(connector_id, tool_id, params, tenant_id=None):
        call_log.append(tool_id)
        if tool_id == fail_on_tool:
            raise RuntimeError(f"Simulated failure on {tool_id}")
        return {"connector": connector_id, "tool": tool_id, "mode": "mock",
                "result": {"ok": True}}

    with mock.patch(
        "app.connectors.registry.ConnectorRegistry.execute_tool",
        side_effect=fake_execute,
    ):
        enqueue = client.post(f"/api/v1/flows/{flow_id}/run")
        assert enqueue.status_code == 202
        return client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()


# ---------------------------------------------------------------------------
# Test 1: on_error: "skip" — run continues past failing step
# ---------------------------------------------------------------------------

def test_skip_policy_continues_after_failure() -> None:
    """Step 1 fails with on_error:skip → Step 2 still runs → run succeeds."""
    _make_flow("fault-skip", [
        {"id": "s1", "name": "Step 1", "description": "Will fail.", "approvedTool": "list_vendors",
         "errorPolicy": {"action": "skip"}},
        {"id": "s2", "name": "Step 2", "description": "Should still run.", "approvedTool": "get_cost_center"},
    ])

    call_log: list[str] = []
    body = _run_with_failing_step("fault-skip", fail_on_tool="list_vendors", call_log=call_log)

    assert body["status"] == "succeeded"
    assert "list_vendors" in call_log
    assert "get_cost_center" in call_log, "Step 2 must run even though Step 1 failed"

    timeline_ids = {s["id"]: s["status"] for s in body["executionTimeline"]}
    assert timeline_ids["s1"] == "skipped"
    assert timeline_ids["s2"] == "succeeded"


# ---------------------------------------------------------------------------
# Test 2: on_error: "retry" — step is retried up to max_retries
# ---------------------------------------------------------------------------

def test_retry_policy_retries_up_to_max() -> None:
    """Step with on_error:retry, max_retries:3 — tool called 4 times total (1 + 3)."""
    _make_flow("fault-retry", [
        {"id": "s1", "name": "Step 1", "description": "Will always fail.",
         "approvedTool": "list_vendors",
         "errorPolicy": {"action": "retry", "maxRetries": 3, "retryDelaySeconds": 0}},
    ])

    call_log: list[str] = []
    body = _run_with_failing_step("fault-retry", fail_on_tool="list_vendors", call_log=call_log)

    # 1 original attempt + 3 retries = 4 calls total
    assert call_log.count("list_vendors") == 4, (
        f"Expected 4 calls (1 + 3 retries), got {call_log.count('list_vendors')}"
    )
    assert body["status"] == "failed"  # exhausted all retries


def test_retry_policy_succeeds_if_retry_works() -> None:
    """Step fails twice then succeeds on the third attempt → run succeeds."""
    _make_flow("fault-retry-success", [
        {"id": "s1", "name": "Step 1", "description": "Fails twice then works.",
         "approvedTool": "list_vendors",
         "errorPolicy": {"action": "retry", "maxRetries": 3, "retryDelaySeconds": 0}},
    ])

    attempt = 0
    call_log: list[str] = []

    def fake_execute(connector_id, tool_id, params, tenant_id=None):
        nonlocal attempt
        call_log.append(tool_id)
        if tool_id == "list_vendors":
            attempt += 1
            if attempt < 3:
                raise RuntimeError("Transient failure")
        return {"connector": connector_id, "tool": tool_id, "mode": "mock", "result": {"ok": True}}

    with mock.patch(
        "app.connectors.registry.ConnectorRegistry.execute_tool",
        side_effect=fake_execute,
    ):
        enqueue = client.post("/api/v1/flows/fault-retry-success/run")
        assert enqueue.status_code == 202
        body = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()

    assert body["status"] == "succeeded"
    assert call_log.count("list_vendors") == 3  # failed twice, succeeded on 3rd


# ---------------------------------------------------------------------------
# Test 3: on_error: "stop" (default) — run stops on first failure
# ---------------------------------------------------------------------------

def test_stop_policy_halts_after_failure() -> None:
    """Default on_error:stop — Step 2 must NOT run when Step 1 fails."""
    _make_flow("fault-stop", [
        {"id": "s1", "name": "Step 1", "description": "Will fail.", "approvedTool": "list_vendors"},
        {"id": "s2", "name": "Step 2", "description": "Must not run.", "approvedTool": "get_cost_center"},
    ])

    call_log: list[str] = []
    body = _run_with_failing_step("fault-stop", fail_on_tool="list_vendors", call_log=call_log)

    assert body["status"] == "failed"
    assert "list_vendors" in call_log
    assert "get_cost_center" not in call_log, "Step 2 must not run when stop policy is active"


# ---------------------------------------------------------------------------
# Test 4: stuck run auto-expiry via Beat task
# ---------------------------------------------------------------------------

def test_expire_stuck_runs_marks_old_running_runs_as_timed_out() -> None:
    """Runs in 'running' state for >15 minutes are marked 'timed_out' by the Beat task."""
    from app.core.database import SessionLocal
    from app.db.models import FlowRunRecord
    from app.worker.beat_tasks import expire_stuck_runs

    old_started = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
    recent_started = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()

    with SessionLocal() as session:
        session.add(FlowRunRecord(
            tenant_id=1, request_id="stuck-old", flow_id="test-flow",
            status="running", started_at=old_started, completed_at=None,
            tools_used=[], message="", data={}, execution_timeline=[],
        ))
        session.add(FlowRunRecord(
            tenant_id=1, request_id="stuck-recent", flow_id="test-flow",
            status="running", started_at=recent_started, completed_at=None,
            tools_used=[], message="", data={}, execution_timeline=[],
        ))
        session.commit()

    expire_stuck_runs()

    with SessionLocal() as session:
        from sqlalchemy import select
        records = {
            r.request_id: r.status
            for r in session.scalars(
                select(FlowRunRecord).where(
                    FlowRunRecord.request_id.in_(["stuck-old", "stuck-recent"])
                )
            ).all()
        }

    assert records["stuck-old"] == "timed_out", "Run >15 min must be marked timed_out"
    assert records["stuck-recent"] == "running", "Run <15 min must remain running"
