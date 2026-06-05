"""Release 6.0 — ConnectorRegistry and generic connector API tests."""
from fastapi.testclient import TestClient

from app.connectors import connector_registry
from app.connectors.base import ConnectorPlugin
from app.main import app
from app.services.audit_service import audit_service

client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()


# ── Unit tests: ConnectorRegistry ─────────────────────────────────────────────

def test_registry_contains_all_eight_connectors() -> None:
    ids = connector_registry.list_ids()
    expected = {"netsuite", "salesforce", "sap", "oracle", "hcm", "postgres", "rest-api", "slack"}
    assert expected <= set(ids), f"Missing connectors: {expected - set(ids)}"


def test_registry_each_plugin_satisfies_protocol() -> None:
    for cid in connector_registry.list_ids():
        plugin = connector_registry.get(cid)
        assert isinstance(plugin, ConnectorPlugin), f"{cid} does not satisfy ConnectorPlugin"
        assert plugin.connector_id == cid
        assert plugin.name
        assert plugin.logo_slug
        assert plugin.auth_scheme in ("none", "api_key", "oauth2", "basic", "token_based")


def test_registry_list_tools_returns_nonempty_list_for_all_connectors() -> None:
    for cid in connector_registry.list_ids():
        tools = connector_registry.get_tools(cid)
        assert len(tools) >= 1, f"Connector {cid!r} has no tools"
        for t in tools:
            assert t.tool_id
            assert t.label
            assert t.description
            assert t.connector_id == cid


def test_registry_execute_tool_succeeds_in_mock_mode() -> None:
    # Pick one tool from each connector and execute it
    sample_tools = {
        "netsuite": "cfo.dashboard_summary",
        "salesforce": "list_opportunities",
        "sap": "get_gl_balance",
        "oracle": "list_periods",
        "hcm": "get_headcount",
        "postgres": "list_approved_templates",
        "rest-api": "http_get",
        "slack": "list_channels",
    }
    for cid, tool_id in sample_tools.items():
        result = connector_registry.execute_tool(cid, tool_id, params={})
        assert isinstance(result, dict), f"{cid}.{tool_id} did not return dict"


def test_registry_unknown_connector_raises_key_error() -> None:
    try:
        connector_registry.get("not-a-real-connector")
        raise AssertionError("Expected KeyError")
    except KeyError:
        pass


def test_registry_unknown_tool_raises_key_error() -> None:
    try:
        connector_registry.execute_tool("netsuite", "nonexistent.tool", params={})
        raise AssertionError("Expected KeyError")
    except KeyError:
        pass


def test_registry_test_connection_returns_ok_true() -> None:
    for cid in connector_registry.list_ids():
        result = connector_registry.get(cid).test_connection()
        assert result.get("ok") is True, f"{cid}.test_connection() did not return ok=True"


# ── HTTP API tests: generic connector routes ──────────────────────────────────

def test_api_list_connectors_returns_all_eight() -> None:
    resp = client.get("/api/v1/connectors")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    ids = {c["connectorId"] for c in body}
    expected = {"netsuite", "salesforce", "sap", "oracle", "hcm", "postgres", "rest-api", "slack"}
    assert expected <= ids, f"Missing: {expected - ids}"


def test_api_list_connectors_schema_has_required_fields() -> None:
    resp = client.get("/api/v1/connectors")
    assert resp.status_code == 200
    for connector in resp.json():
        assert "connectorId" in connector
        assert "name" in connector
        assert "logoSlug" in connector
        assert "authScheme" in connector
        assert "status" in connector
        assert "mode" in connector
        assert "toolCount" in connector
        assert connector["toolCount"] >= 1


def test_api_get_connector_by_id_returns_definition_with_tools() -> None:
    resp = client.get("/api/v1/connectors/salesforce")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connectorId"] == "salesforce"
    assert body["name"] == "Salesforce CRM"
    assert body["authScheme"] == "oauth2"
    tools = body["tools"]
    assert len(tools) >= 1
    tool_ids = {t["toolId"] for t in tools}
    assert "list_opportunities" in tool_ids


def test_api_get_connector_unknown_returns_404() -> None:
    resp = client.get("/api/v1/connectors/not-a-connector")
    assert resp.status_code == 404


def test_api_get_connector_tools_returns_list() -> None:
    resp = client.get("/api/v1/connectors/slack/tools")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    tool_ids = {t["toolId"] for t in body}
    assert "post_message" in tool_ids
    assert "list_channels" in tool_ids


def test_api_test_connector_returns_ok_true_in_mock_mode() -> None:
    for cid in ["netsuite", "salesforce", "sap", "oracle", "hcm", "postgres", "rest-api", "slack"]:
        resp = client.post(f"/api/v1/connectors/{cid}/test")
        assert resp.status_code == 200, f"{cid} test failed: {resp.text}"
        assert resp.json()["ok"] is True, f"{cid} returned ok != True"


def test_api_test_unknown_connector_returns_404() -> None:
    resp = client.post("/api/v1/connectors/not-real/test")
    assert resp.status_code == 404


# ── Step-driven flow execution via registry ───────────────────────────────────

def test_step_driven_execution_netsuite_flow_succeeds() -> None:
    """demo-netsuite-cfo-dashboard runs step-by-step via connector registry."""
    enqueue = client.post("/api/v1/flows/demo-netsuite-cfo-dashboard/run")
    assert enqueue.status_code == 202
    request_id = enqueue.json()["requestId"]
    run = client.get(f"/api/v1/flows/runs/{request_id}").json()
    assert run["status"] == "succeeded"
    assert len(run["executionTimeline"]) == 2
    assert all(s["status"] == "succeeded" for s in run["executionTimeline"])
    assert "cfo.dashboard_summary" in run["toolsUsed"]
    assert "cfo.pl_vs_budget" in run["toolsUsed"]


def test_step_driven_execution_salesforce_flow_succeeds() -> None:
    enqueue = client.post("/api/v1/flows/demo-salesforce-opportunity-sync/run")
    assert enqueue.status_code == 202
    run = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()
    assert run["status"] == "succeeded"
    assert "list_opportunities" in run["toolsUsed"]


def test_step_driven_execution_slack_flow_succeeds() -> None:
    enqueue = client.post("/api/v1/flows/demo-slack-alert-dispatch/run")
    assert enqueue.status_code == 202
    run = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()
    assert run["status"] == "succeeded"
    assert "list_channels" in run["toolsUsed"]
    assert "post_message" in run["toolsUsed"]


def test_step_driven_execution_unknown_tool_fails_with_timeline_entry() -> None:
    """A custom flow referencing a non-existent tool must fail with timeline entry."""
    # Create a flow with a clearly invalid tool
    create_resp = client.post(
        "/api/v1/flows/definitions",
        json={
            "flowId": "bad-tool-test-flow",
            "name": "Bad tool test",
            "description": "Flow using a non-existent connector tool for test coverage.",
            "sourceConnector": "netsuite",
            "targetModule": "test_module",
            "status": "draft",
            "triggerType": "manual",
            "steps": [
                {
                    "id": "bad-step",
                    "name": "Bad step",
                    "description": "Calls a tool that does not exist in the registry.",
                    "approvedTool": "nonexistent.tool.call",
                }
            ],
        },
    )
    assert create_resp.status_code == 200

    # Publish through lifecycle
    flow_id = create_resp.json()["flowId"]
    for action in ["submit_for_approval", "approve", "publish"]:
        r = client.post(f"/api/v1/flows/{flow_id}/lifecycle", json={"action": action})
        assert r.status_code == 200, f"Lifecycle {action} failed: {r.text}"

    # Run and expect failure
    enqueue = client.post(f"/api/v1/flows/{flow_id}/run")
    assert enqueue.status_code == 202
    run = client.get(f"/api/v1/flows/runs/{enqueue.json()['requestId']}").json()
    assert run["status"] == "failed"
    assert run["executionTimeline"][0]["status"] == "failed"
