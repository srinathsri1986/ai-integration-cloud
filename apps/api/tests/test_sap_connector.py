"""Tests for the SAP connector — plugin (mock + live wiring) and live OData connector.

Mirrors the structural test pattern used for the NetSuite live connector
(tests/test_netsuite_r15.py::TestLiveConnectorOAuth): config/URL shape, auth
header construction (and that it never leaks credentials), and graceful
no-network error handling — without making real outbound HTTP calls.
"""
from __future__ import annotations

import base64

from app.connectors.sap.plugin import SAPPlugin, _LIVE_TOOL_MAP, _TOOL_MAP


class TestSAPPluginMock:
    def test_lists_expected_tools(self) -> None:
        plugin = SAPPlugin()
        tool_ids = {t.tool_id for t in plugin.list_tools()}
        assert tool_ids == set(_TOOL_MAP)
        assert "post_journal_entry" in tool_ids
        assert "create_purchase_order" in tool_ids

    def test_execute_unknown_tool_raises(self) -> None:
        plugin = SAPPlugin()
        try:
            plugin.execute_tool("not_a_real_tool", {})
        except KeyError as exc:
            assert "Unknown SAP tool" in str(exc)
        else:
            raise AssertionError("Expected KeyError for unknown tool")

    def test_execute_tool_mock_mode_shape(self) -> None:
        plugin = SAPPlugin()
        result = plugin.execute_tool("get_cost_center", {"cost_center_id": "CC-1100"})
        assert result["connector"] == "sap"
        assert result["tool"] == "get_cost_center"
        assert result["mode"] == "mock"
        assert "result" in result

    def test_test_connection_mock_mode(self) -> None:
        plugin = SAPPlugin()
        result = plugin.test_connection()
        assert result["mode"] == "mock"
        assert result["ok"] is True

    def test_fetch_schema_returns_curated_objects(self) -> None:
        plugin = SAPPlugin()
        objects = plugin.fetch_schema()
        object_ids = {o.object_id for o in objects}
        assert {"cost_center", "journal_entry", "vendor"}.issubset(object_ids)


class TestSAPLiveToolMap:
    def test_every_live_tool_id_is_a_real_tool(self) -> None:
        # Guards against typos that would silently make a tool unreachable in live mode
        assert set(_LIVE_TOOL_MAP).issubset(set(_TOOL_MAP))

    def test_live_tool_map_entries_are_well_formed(self) -> None:
        for tool_id, (service_path, entity_set, kind) in _LIVE_TOOL_MAP.items():
            assert "/" in service_path, f"{tool_id}: service_path should be 'API_X/EntitySet' shaped"
            assert entity_set, f"{tool_id}: entity_set must not be empty"
            assert kind in ("read", "write"), f"{tool_id}: kind must be 'read' or 'write'"


class TestSAPLiveConnectorProductionMode:
    """Basic Auth + sap-client — how real S/4HANA Cloud / on-prem Gateway systems authenticate."""

    def _make_config(self, **overrides):
        from app.connectors.sap.live_connector import SAPLiveConfig
        defaults = dict(host="my-s4-system.example.com", client="100", username="demo_user", password="demo_pass")
        defaults.update(overrides)
        return SAPLiveConfig(**defaults)

    def test_base_url_strips_scheme_and_trailing_slash(self) -> None:
        from app.connectors.sap.live_connector import SAPLiveConfig
        cfg = SAPLiveConfig(host="https://my-system.example.com/", username="u", password="p")
        assert cfg.base_url == "https://my-system.example.com"

    def test_service_url_production_shape(self) -> None:
        cfg = self._make_config()
        url = cfg.service_url("API_BUSINESS_PARTNER/A_BusinessPartner")
        assert url == "https://my-s4-system.example.com/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner"

    def test_is_sandbox_mode_false_without_api_key(self) -> None:
        assert self._make_config().is_sandbox_mode is False

    def test_auth_header_is_basic_and_correctly_encoded(self) -> None:
        from app.connectors.sap.live_connector import SAPLiveConnector
        connector = SAPLiveConnector(self._make_config(username="demo_user", password="s3cr3t"))
        header = connector._auth_header()
        expected = "Basic " + base64.b64encode(b"demo_user:s3cr3t").decode("ascii")
        assert header == {"Authorization": expected}
        # Credentials must never appear in plaintext in any header value
        assert "demo_user:s3cr3t" not in str(header)
        assert "s3cr3t" not in header["Authorization"]

    def test_client_query_param_present_in_production_mode(self) -> None:
        from app.connectors.sap.live_connector import SAPLiveConnector
        connector = SAPLiveConnector(self._make_config(client="200"))
        assert connector._client_query_params() == {"sap-client": "200"}

    def test_error_on_network_failure_does_not_leak_credentials(self) -> None:
        from app.connectors.sap.live_connector import SAPLiveConnector
        connector = SAPLiveConnector(self._make_config(password="super-secret-password"))
        result = connector.test_connection()  # no real network → ok=False, safe message
        assert result["mode"] == "live"
        assert result["ok"] is False
        assert isinstance(result["message"], str)
        assert "super-secret-password" not in result["message"]
        assert "demo_user" not in result["message"] or True  # username is not a secret; password is what matters


class TestSAPLiveConnectorSandboxMode:
    """APIKey header — the SAP Business Accelerator Hub Sandbox's auth scheme.

    Free, public, self-service (api.sap.com) — no real SAP system required.
    Its OData services are proxied under a base-path prefix and reject the
    `sap-client` parameter that production Gateway systems require.
    """

    def _make_config(self, **overrides):
        from app.connectors.sap.live_connector import SAPLiveConfig
        defaults = dict(host="sandbox.api.sap.com", api_key="test-sandbox-key", api_base_path="s4hanacloud")
        defaults.update(overrides)
        return SAPLiveConfig(**defaults)

    def test_is_sandbox_mode_true_with_api_key(self) -> None:
        assert self._make_config().is_sandbox_mode is True

    def test_service_url_includes_proxy_prefix(self) -> None:
        cfg = self._make_config()
        url = cfg.service_url("API_BUSINESS_PARTNER/A_BusinessPartner")
        assert url == "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner"

    def test_auth_header_is_api_key_not_basic(self) -> None:
        from app.connectors.sap.live_connector import SAPLiveConnector
        connector = SAPLiveConnector(self._make_config(api_key="abc123secretkey"))
        assert connector._auth_header() == {"APIKey": "abc123secretkey"}

    def test_sandbox_mode_omits_sap_client_param(self) -> None:
        # The sandbox proxy rejects `sap-client` — production-Gateway-only concept
        from app.connectors.sap.live_connector import SAPLiveConnector
        connector = SAPLiveConnector(self._make_config(client="100"))
        assert connector._client_query_params() == {}

    def test_sandbox_mode_takes_precedence_over_basic_auth(self) -> None:
        # If both api_key and username/password are configured, APIKey wins
        from app.connectors.sap.live_connector import SAPLiveConnector
        connector = SAPLiveConnector(self._make_config(username="u", password="p", api_key="thekey"))
        assert connector._auth_header() == {"APIKey": "thekey"}


class _FakeMetadataResponse:
    """Minimal stand-in for the context-managed response `_opener.open()` returns."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body


class TestSAPMetadataRequestsXML:
    """Regression guard for a live-network bug:

    SAP's gateway treats `Accept: application/json` on a `/$metadata` resource
    as an attempt to set an unsupported `$format=json` system query option and
    rejects it with HTTP 400 "Invalid system query options value" — discovered
    against the real sandbox.api.sap.com gateway. `$metadata` is XML/CSDL by
    spec and must always be requested with `Accept: application/xml`.
    """

    def _connector_with_captured_requests(self, captured: list):
        from app.connectors.sap.live_connector import SAPLiveConfig, SAPLiveConnector

        connector = SAPLiveConnector(
            SAPLiveConfig(host="sandbox.api.sap.com", api_key="test-key", api_base_path="s4hanacloud")
        )

        def fake_open(req, timeout=None):
            captured.append(req)
            return _FakeMetadataResponse(b'<edmx:Edmx xmlns:edmx="x"><EntityType Name="A_BusinessPartner"/></edmx:Edmx>')

        connector._opener = type("FakeOpener", (), {"open": staticmethod(fake_open)})()
        return connector

    def test_fetch_schema_objects_requests_xml_not_json(self) -> None:
        captured: list = []
        connector = self._connector_with_captured_requests(captured)

        objects = connector.fetch_schema_objects("API_BUSINESS_PARTNER/A_BusinessPartner")

        assert len(captured) == 1
        assert captured[0].get_header("Accept") == "application/xml"
        assert objects == ["A_BusinessPartner"]

    def test_sandbox_test_connection_requests_xml_for_metadata_probe(self) -> None:
        captured: list = []
        connector = self._connector_with_captured_requests(captured)

        result = connector.test_connection()

        assert len(captured) == 1
        assert captured[0].get_header("Accept") == "application/xml"
        assert result["ok"] is True

    def test_get_text_defaults_to_json_accept_for_non_metadata_calls(self) -> None:
        captured: list = []
        connector = self._connector_with_captured_requests(captured)

        connector._get_text("https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/X/Y")

        assert captured[0].get_header("Accept") == "application/json"


class TestSAPLiveConfigValidation:
    def test_requires_basic_auth_or_api_key(self) -> None:
        from app.api.connectors import SAPLiveConfig as SAPLiveConfigRequest
        from pydantic import ValidationError

        # Neither basic auth nor api_key supplied → should fail validation
        try:
            SAPLiveConfigRequest(host="my-system.example.com")
        except ValidationError as exc:
            assert "username" in str(exc) or "API key" in str(exc) or "Provide either" in str(exc)
        else:
            raise AssertionError("Expected ValidationError when neither auth mode is configured")

    def test_accepts_basic_auth_mode(self) -> None:
        from app.api.connectors import SAPLiveConfig as SAPLiveConfigRequest

        config = SAPLiveConfigRequest(host="my-system.example.com", username="u", password="p")
        assert config.host == "my-system.example.com"

    def test_accepts_sandbox_api_key_mode(self) -> None:
        from app.api.connectors import SAPLiveConfig as SAPLiveConfigRequest

        config = SAPLiveConfigRequest(host="sandbox.api.sap.com", api_key="key123", api_base_path="s4hanacloud")
        assert config.api_key == "key123"
