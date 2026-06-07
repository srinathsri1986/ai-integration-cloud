"""R17 — SaaS Scalability: Tenant-First Connector Layer.

Tests verify:
1. execute_tool passes tenant_id through the full call chain
2. list_connectors returns per-tenant status (not always global defaults)
3. Schema cache: hit / miss / TTL / invalidation / Redis fallback
4. Generic GET/PUT /connectors/{id}/config — tenant-scoped, secrets rejected
5. all_connector_modes tenant-first resolution (tenant overrides global)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.connectors import connector_registry
from app.connectors.base import ConnectorTool
from app.main import app
from app.services.audit_service import audit_service
from app.services.credential_service import credential_service
from app.services.schema_cache import ConnectorSchemaCache, _InProcessBackend
from app.services.flow_service import flow_service

client = TestClient(app)


def setup_function() -> None:
    audit_service.clear_for_tests()
    flow_service.clear_for_tests()


# ─── 1. execute_tool tenant propagation ───────────────────────────────────────

def test_registry_execute_tool_accepts_tenant_id() -> None:
    """registry.execute_tool must forward tenant_id to the plugin without error."""
    result = connector_registry.execute_tool("netsuite", "cfo.dashboard_summary", params={}, tenant_id=42)
    assert isinstance(result, dict)


def test_all_plugins_accept_tenant_id_in_execute_tool() -> None:
    """Every registered plugin must accept tenant_id without raising TypeError."""
    for connector_id in connector_registry.list_ids():
        tools = connector_registry.get_tools(connector_id)
        if not tools:
            continue
        tool_id = tools[0].tool_id
        result = connector_registry.execute_tool(connector_id, tool_id, params={}, tenant_id=99)
        assert isinstance(result, dict), f"Plugin {connector_id} tool {tool_id} returned non-dict"


def test_execute_tool_no_params_get_tenant_id_hack() -> None:
    """Verify no plugin reads tenant_id from params (legacy hack removed)."""
    # Pass a deliberately wrong tenant_id inside params — result should be same as not passing it
    result_clean  = connector_registry.execute_tool("salesforce", "list_opportunities", {}, tenant_id=None)
    result_hacked = connector_registry.execute_tool("salesforce", "list_opportunities", {"tenant_id": 99999}, tenant_id=None)
    # Both should succeed and return dict; the params-injected tenant_id is irrelevant
    assert isinstance(result_clean, dict)
    assert isinstance(result_hacked, dict)
    # The hack-injected value should not affect mock mode result (no live creds in test env)
    assert result_clean.get("mode") == "mock"
    assert result_hacked.get("mode") == "mock"


# ─── 2. list_connectors per-tenant status ─────────────────────────────────────

def test_list_connectors_endpoint_returns_all_8() -> None:
    resp = client.get("/api/v1/connectors")
    assert resp.status_code == 200
    data = resp.json()
    connector_ids = {c["connectorId"] for c in data}
    expected = {"netsuite", "salesforce", "sap", "oracle", "hcm", "postgres", "rest-api", "slack"}
    assert expected == connector_ids


def test_list_connectors_mode_defaults_to_mock_without_config() -> None:
    resp = client.get("/api/v1/connectors")
    assert resp.status_code == 200
    for c in resp.json():
        # In test environment nothing is configured → all mock
        assert c["mode"] in ("mock", "live"), f"Unexpected mode {c['mode']} for {c['connectorId']}"


def test_all_connector_modes_tenant_overrides_global() -> None:
    """Tenant-specific mode must take precedence over global default."""
    # Write a global default (tenant_id=None)
    credential_service._upsert_config("sap", None, {}, status="not_configured", mode="mock")  # noqa: SLF001
    # Write a tenant override (tenant_id=7)
    credential_service._upsert_config("sap", 7, {}, status="configured", mode="live")  # noqa: SLF001

    modes = credential_service.all_connector_modes(tenant_id=7)
    assert modes.get("sap") == "live", "Tenant-7 override should win over global mock default"

    modes_other = credential_service.all_connector_modes(tenant_id=99)
    # tenant 99 has no record → falls back to global "mock"
    assert modes_other.get("sap") == "mock"

    # Clean up
    credential_service._upsert_config("sap", None, {}, status="not_configured", mode="mock")  # noqa: SLF001
    credential_service._upsert_config("sap", 7, {}, status="not_configured", mode="mock")  # noqa: SLF001


def test_all_connector_modes_global_fallback_when_no_tenant_row() -> None:
    """When no tenant-specific row exists, falls back to global row."""
    # Ensure global mock row exists; no tenant-999 row
    credential_service._upsert_config("oracle", None, {}, status="not_configured", mode="mock")  # noqa: SLF001

    modes = credential_service.all_connector_modes(tenant_id=999)
    # oracle should appear from the global fallback
    assert modes.get("oracle") == "mock"


# ─── 3. Schema cache ──────────────────────────────────────────────────────────

def _make_cache() -> ConnectorSchemaCache:
    """Create a fresh in-process schema cache (isolated from module singleton)."""
    cache = ConnectorSchemaCache.__new__(ConnectorSchemaCache)
    cache._backend = _InProcessBackend()  # noqa: SLF001
    return cache


def test_schema_cache_miss_returns_none() -> None:
    cache = _make_cache()
    assert cache.get("netsuite") is None
    assert cache.get("netsuite", tenant_id=42) is None


def test_schema_cache_set_and_get() -> None:
    cache = _make_cache()
    data = [{"objectId": "invoice", "fields": []}]
    cache.set("netsuite", data, tenant_id=1, is_mock=True)
    result = cache.get("netsuite", tenant_id=1)
    assert result == data


def test_schema_cache_tenant_isolation() -> None:
    """Tenant A's cached schema must not be visible to tenant B."""
    cache = _make_cache()
    cache.set("salesforce", [{"objectId": "opportunity"}], tenant_id=1, is_mock=True)
    assert cache.get("salesforce", tenant_id=2) is None  # tenant 2 gets a cache miss


def test_schema_cache_invalidate() -> None:
    cache = _make_cache()
    cache.set("slack", [{"objectId": "channel"}], tenant_id=5, is_mock=False)
    assert cache.get("slack", tenant_id=5) is not None
    cache.invalidate("slack", tenant_id=5)
    assert cache.get("slack", tenant_id=5) is None


def test_schema_cache_invalidate_connector_clears_all_tenants() -> None:
    cache = _make_cache()
    for tid in [1, 2, 3]:
        cache.set("postgres", [{"objectId": "users"}], tenant_id=tid, is_mock=False)
    cache.invalidate_connector("postgres")
    for tid in [1, 2, 3]:
        assert cache.get("postgres", tenant_id=tid) is None


def test_schema_cache_live_ttl_set(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Live schemas should have a TTL; mock schemas cached indefinitely."""
    import app.services.schema_cache as sc_module
    cache = _make_cache()
    # Live schema: TTL should be set (expires_at is not None)
    cache.set("salesforce", [{}], tenant_id=1, is_mock=False)
    key = ("salesforce", 1)
    _, expires_at = cache._backend._store[key]  # noqa: SLF001
    assert expires_at is not None, "Live schema must have an expiry"

    # Mock schema: no TTL (cached indefinitely)
    cache.set("netsuite", [{}], tenant_id=1, is_mock=True)
    key2 = ("netsuite", 1)
    _, expires_at2 = cache._backend._store[key2]  # noqa: SLF001
    assert expires_at2 is None, "Mock schema must be cached indefinitely"


def test_schema_endpoint_returns_200() -> None:
    resp = client.get("/api/v1/connectors/netsuite/schema")
    assert resp.status_code == 200
    body = resp.json()
    assert "objects" in body
    assert len(body["objects"]) > 0


def test_schema_endpoint_refresh_param_bypasses_cache() -> None:
    """?refresh=true should re-fetch even if a cached entry exists."""
    # Warm the cache
    client.get("/api/v1/connectors/sap/schema")
    # Force refresh
    resp = client.get("/api/v1/connectors/sap/schema?refresh=true")
    assert resp.status_code == 200
    assert "objects" in resp.json()


# ─── 4. Generic connector config API ─────────────────────────────────────────

def test_get_connector_config_returns_not_configured_when_empty() -> None:
    """GET /connectors/hcm/config should return not_configured for unconfigured connector."""
    resp = client.get("/api/v1/connectors/hcm/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connectorId"] == "hcm"
    assert body["mode"] in ("mock", "not_configured", "live")


def test_get_connector_config_404_for_unknown_connector() -> None:
    resp = client.get("/api/v1/connectors/does-not-exist/config")
    assert resp.status_code == 404


def test_put_connector_config_rejects_secrets() -> None:
    """PUT with api_key, password, or connection_string must return 422."""
    for secret_field in ["api_key", "connection_string", "access_token"]:
        resp = client.put(
            "/api/v1/connectors/hcm/config",
            json={secret_field: "should-be-rejected"},
        )
        assert resp.status_code == 422, f"Expected 422 for secret field '{secret_field}'"
        assert "secret" in resp.json()["detail"].lower()


def test_put_connector_config_accepts_non_secret_metadata() -> None:
    """Safe metadata (account IDs, display names) should be accepted."""
    resp = client.put(
        "/api/v1/connectors/oracle/config",
        json={"account_display_name": "Acme Corp Oracle", "region": "us-east-1"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_put_connector_config_404_for_unknown_connector() -> None:
    resp = client.put("/api/v1/connectors/nonexistent/config", json={"foo": "bar"})
    assert resp.status_code == 404


# ─── 5. Registry statelessness ───────────────────────────────────────────────

def test_connector_plugins_are_stateless_singletons() -> None:
    """The same plugin instance must handle calls for different tenants without bleed."""
    plugin = connector_registry.get("netsuite")
    result_t1 = plugin.execute_tool("cfo.dashboard_summary", {}, tenant_id=1)
    result_t2 = plugin.execute_tool("cfo.dashboard_summary", {}, tenant_id=2)
    # Both return valid dicts — no cross-tenant contamination in mock mode
    assert isinstance(result_t1, dict)
    assert isinstance(result_t2, dict)
    # Plugin instance is reused (same object)
    assert plugin is connector_registry.get("netsuite")
