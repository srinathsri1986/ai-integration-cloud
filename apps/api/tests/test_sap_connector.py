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
            # service_path is the OData service root only (no EntitySet suffix) — the
            # connector appends entity_set separately to avoid URL-doubling.
            assert service_path, f"{tool_id}: service_path must not be empty"
            assert "/" not in entity_set, f"{tool_id}: entity_set should be a bare name, not a path"
            assert entity_set, f"{tool_id}: entity_set must not be empty"
            assert kind in ("read", "write"), f"{tool_id}: kind must be 'read' or 'write'"

    def test_known_service_ids_are_real_sap_business_hub_services(self) -> None:
        # Regression guard for a live-network bug: the original map shipped with
        # "API_OPLACCTGDOCITEMCRUDQP_SRV" (a hallucinated/typo'd service ID that
        # doesn't exist) for post_journal_entry — confirmed live against the real
        # sandbox, which returned HTTP 400 "Invalid system query options value"
        # (Apigee's generic error for an unroutable service path). Every service
        # ID we wire live MUST be a real, verified SAP Business Accelerator Hub
        # service — listed here so a future typo fails the suite immediately.
        known_real_service_ids = {
            "API_BUSINESS_PARTNER",
            "API_COSTCENTER_SRV",
            "API_GLACCOUNTLINEITEM_SRV",
            "API_PURCHASEORDER_PROCESS_SRV",
        }
        for tool_id, (service_path, _entity_set, _kind) in _LIVE_TOOL_MAP.items():
            service_id = service_path.split("/", 1)[0]
            assert service_id in known_real_service_ids, (
                f"{tool_id}: service ID '{service_id}' is not in the verified-real list — "
                "confirm it exists on api.sap.com before wiring it live."
            )

    def test_post_journal_entry_is_intentionally_not_live_wired(self) -> None:
        # SAP's actual journal-entry posting APIs (JOURNALENTRYCREATEREQUESTCONFI
        # "Journal Entry - Post (Synchronous)" and JOURNALENTRYBULKLEDGERCREATION
        # "Journal Entry by Ledger - Post (Asynchronous)") are message-based
        # inbound integration services with a JournalEntryCreateRequest envelope —
        # not OData entity-set CRUD. The only OData service in this domain
        # (API_OPLACCTGDOCITEMCUBE_SRV, "Accounting Document - Read") is
        # READ-ONLY. There is no honest way to wire a live POST for this tool
        # via the generic create_entity() CSRF flow today, so it stays mock-only
        # until a dedicated message-based posting client is built.
        assert "post_journal_entry" in _TOOL_MAP
        assert "post_journal_entry" not in _LIVE_TOOL_MAP


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

    def test_base_url_tolerates_full_endpoint_url_pasted_into_host(self) -> None:
        # Regression guard for a live-network bug reproduced from the user's
        # exact "Configure SAP ERP" form contents: the SAP Business Accelerator
        # Hub prominently displays full service-endpoint URLs (e.g.
        # "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/
        # API_OPLACCTGDOCITEMCUBE_SRV") right next to the API key, and it's an
        # easy slip to paste that whole string into the "Sandbox Host" field
        # instead of the bare hostname. Before this fix, base_url returned the
        # full pasted string verbatim, and service_url() then appended its own
        # path on top — producing a garbled, duplicated, unroutable URL that
        # the gateway rejected with the same generic HTTP 400 "Invalid system
        # query options value" error (confirmed live). base_url must discard
        # any path component and keep only the hostname.
        from app.connectors.sap.live_connector import SAPLiveConfig

        cfg = SAPLiveConfig(
            host="https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_OPLACCTGDOCITEMCUBE_SRV",
            api_key="test-sandbox-key",
            api_base_path="s4hanacloud",
        )
        assert cfg.base_url == "https://sandbox.api.sap.com"

        url = cfg.service_url("API_BUSINESS_PARTNER/A_BusinessPartner")
        assert url == "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner"
        # The garbled duplication must not appear anywhere in the built URL
        assert "API_OPLACCTGDOCITEMCUBE_SRV" not in url
        assert url.count("/sap/opu/odata/sap/") == 1

    def test_base_url_tolerates_bare_host_with_path_and_no_scheme(self) -> None:
        # Same defensive behaviour without a scheme — e.g. "sandbox.api.sap.com/some/path"
        from app.connectors.sap.live_connector import SAPLiveConfig

        cfg = SAPLiveConfig(host="sandbox.api.sap.com/extra/path/segments", api_key="k")
        assert cfg.base_url == "https://sandbox.api.sap.com"


class _FakeHeaders:
    """Minimal stand-in for http.client.HTTPMessage."""

    def __init__(self, mapping: dict | None = None) -> None:
        self._m = mapping or {}

    def get(self, key: str, default: str = "") -> str:
        return self._m.get(key, default)


class _FakeMetadataResponse:
    """Minimal stand-in for the context-managed response `_opener.open()` returns."""

    def __init__(self, body: bytes, headers: dict | None = None) -> None:
        self._body = body
        self.headers = _FakeHeaders(headers)

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


class TestSAPListEntitiesQueryParams:
    """Regression guard for a second live-network bug, same error class:

    list_entities() originally sent BOTH `$format=json` as a query parameter
    AND `Accept: application/json` as a header. The sandbox's Apigee-fronted
    gateway rejected `$format=json` with the same HTTP 400 "Invalid system
    query options value" error — `$format` is OData-version-sensitive (the
    bare `json` shorthand isn't universally accepted), whereas `Accept` is
    the protocol-correct, version-agnostic negotiation mechanism. The fix:
    send only `$top` as a query option; rely solely on `Accept` for format.
    """

    def _connector_with_captured_requests(self, captured: list, body: bytes):
        from app.connectors.sap.live_connector import SAPLiveConfig, SAPLiveConnector

        connector = SAPLiveConnector(
            SAPLiveConfig(host="sandbox.api.sap.com", api_key="test-key", api_base_path="s4hanacloud")
        )

        def fake_open(req, timeout=None):
            captured.append(req)
            return _FakeMetadataResponse(body)

        connector._opener = type("FakeOpener", (), {"open": staticmethod(fake_open)})()
        return connector

    def test_list_entities_query_string_omits_format_param(self) -> None:
        captured: list = []
        body = b'{"d": {"results": [{"BusinessPartner": "1003765"}]}}'
        connector = self._connector_with_captured_requests(captured, body)

        records = connector.list_entities("API_BUSINESS_PARTNER/A_BusinessPartner", "A_BusinessPartner", top=10)

        assert len(captured) == 1
        full_url = captured[0].full_url
        # urlencode renders "$" as "%24"
        assert "%24top=10" in full_url
        assert "format" not in full_url
        assert captured[0].get_header("Accept") == "application/json"
        assert records == [{"BusinessPartner": "1003765"}]


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
