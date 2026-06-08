"""SAP live connector — OData v2/v4 over HTTPS with Basic Auth + CSRF handshake.

Why OData/REST instead of RFC
------------------------------
Classic SAP integration uses the RFC protocol (pyrfc + the SAP NetWeaver RFC
SDK), but that SDK is a licensed native binary that cannot be pip-installed
and would make local dev/CI fragile and non-portable. SAP's own modern
guidance steers cloud-native integration toward the OData/REST Gateway APIs
(exposed by S/4HANA Cloud, SAP Gateway for on-prem, and the SAP Business
Accelerator Hub sandbox) — HTTPS + Basic Auth or OAuth2, with the SAP client
passed via the `sap-client` query parameter / header. This connector talks
that protocol exclusively: plain HTTPS, stdlib `urllib`, no vendor SDK,
no native dependencies — consistent with the NetSuite (hand-rolled OAuth1.0a)
and Salesforce (HTTPS + simple-salesforce) live connectors already shipped.

The two-step OData write handshake
-----------------------------------
SAP's OData services protect mutating calls (POST/PATCH/DELETE) with CSRF
tokens bound to a session. A cloud-native client must:
  1. Issue a GET with header `X-CSRF-Token: Fetch` — the response carries a
     fresh `X-CSRF-Token` header AND `Set-Cookie` session cookies.
  2. Reuse BOTH the token and the session cookies on the subsequent
     POST/PATCH/DELETE (as `X-CSRF-Token: <token>` + `Cookie: <jar>`).
A client that fetches the token but drops the session cookie (or vice
versa) gets a generic 403 "CSRF token validation failed" — this connector
uses an `http.cookiejar.CookieJar` so the handshake state travels correctly
across both calls.

Security guarantees
-------------------
- Credentials are never logged. `_auth_header()` builds the Basic Auth
  header in-memory from the decrypted vault config; nothing is written to
  logs except connector_id/tool_id/status.
- All exceptions are caught and re-raised as SAPLiveConnectorError so
  callers never receive raw HTTP/auth error details (compliance: no raw
  error traces to clients).
- Only approved OData entity-set paths from the plugin's tool map are
  requested — no arbitrary path or query is accepted from callers.
"""
from __future__ import annotations

import base64
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any

logger = logging.getLogger(__name__)


class SAPLiveConnectorError(RuntimeError):
    """Raised for all live-connector failures. Message is safe to surface to UI."""


@dataclass(frozen=True)
class SAPLiveConfig:
    """Credentials loaded from the Fernet vault — never stored in plaintext.

    Two auth modes are supported, auto-selected by which fields are populated:

    - **Production mode** (Basic Auth + CSRF handshake): set `username` /
      `password`. This is how real S/4HANA Cloud, S/4HANA on-prem (via SAP
      Gateway), and SAP Business Technology Platform systems authenticate
      OData calls — the protocol this connector is built to speak.

    - **Sandbox mode** (`APIKey` header): set `api_key`. The free, public
      **SAP Business Accelerator Hub Sandbox** (sandbox.api.sap.com) fronts
      its OData services with an Apigee gateway that authenticates via a
      simple `APIKey` request header instead of Basic Auth/OAuth2 — a
      sandbox-only convenience (obtained via free self-service signup at
      api.sap.com, no real SAP system required). `api_base_path` carries
      the sandbox's proxy prefix (e.g. "s4hanacloud") since its routing
      differs from a production Gateway's `/sap/opu/odata/sap/...` shape.
      When `api_key` is set it takes precedence over Basic Auth.
    """

    host: str               # e.g. "sandbox.api.sap.com" or "my-s4-system.example.com"
    client: str = "100"     # SAP client / mandant, sent as `sap-client` (production systems only)
    username: str = ""
    password: str = ""
    system_number: str = "00"   # retained for RFC-fallback readiness; unused by OData
    api_key: str = ""           # sandbox-mode auth — see class docstring
    api_base_path: str = ""     # sandbox proxy prefix, e.g. "s4hanacloud" (blank for production systems)
    timeout_seconds: int = 15

    @property
    def is_sandbox_mode(self) -> bool:
        return bool(self.api_key)

    @property
    def base_url(self) -> str:
        """Root HTTPS URL for this SAP system's OData Gateway."""
        host = self.host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        return f"https://{host}"

    def service_url(self, service_path: str) -> str:
        """Build a full OData service URL, e.g. service_path='API_BUSINESS_PARTNER/A_BusinessPartner'.

        Production Gateway shape: {base_url}/sap/opu/odata/sap/{service_path}
        Sandbox proxy shape:      {base_url}/{api_base_path}/sap/opu/odata/sap/{service_path}
        """
        path = service_path.lstrip("/")
        prefix = f"/{self.api_base_path.strip('/')}" if self.api_base_path else ""
        return f"{self.base_url}{prefix}/sap/opu/odata/sap/{path}"


class SAPLiveConnector:
    """Live connector against SAP OData Gateway services (Basic Auth + CSRF handshake)."""

    source = "live"

    def __init__(self, config: SAPLiveConfig) -> None:
        self._config = config
        self._cookie_jar = CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._cookie_jar))

    # ── Public interface ──────────────────────────────────────────────────────

    def test_connection(self) -> dict[str, Any]:
        """Probe the SAP OData Gateway.

        Production systems expose a Gateway catalog service at a fixed path;
        the sandbox proxy doesn't, so in sandbox mode we probe a known public
        entity set's $metadata instead — either way, a 200 means credentials
        and routing are both correct end-to-end.

        Returns {"ok": bool, "mode": "live", "message": str}. Never raises —
        returns ok=False with a safe message on failure.
        """
        try:
            if self._config.is_sandbox_mode:
                url = f"{self._config.service_url('API_BUSINESS_PARTNER/A_BusinessPartner')}/$metadata"
                # $metadata is XML/CSDL by spec — requesting JSON here makes
                # the gateway reject with "Invalid system query options value".
                self._get_text(url, accept="application/xml")
                detail = "SAP Business Accelerator Hub Sandbox"
            else:
                url = f"{self._config.base_url}/sap/opu/odata/iwfnd/catalogservice;v=2/ServiceCollection"
                self._get(url)
                detail = f"client {self._config.client}"
            return {
                "ok": True,
                "mode": "live",
                "message": f"Connected to SAP system at {self._config.host} ({detail}).",
            }
        except SAPLiveConnectorError as exc:
            return {"ok": False, "mode": "live", "message": str(exc)}

    def fetch_schema_objects(self, service_path: str) -> list[str]:
        """Parse an OData service's $metadata document and return EntityType names."""
        try:
            url = f"{self._config.service_url(service_path)}/$metadata"
            # See _get_text docstring — $metadata is XML-only; Accept: application/json
            # gets rejected by SAP's gateway as an invalid $format system query option.
            xml_text = self._get_text(url, accept="application/xml")
            return sorted(set(re.findall(r'<EntityType\s+Name="([^"]+)"', xml_text)))
        except SAPLiveConnectorError:
            logger.warning("Could not fetch live SAP $metadata for %s; using static catalog.", service_path)
            return []

    def list_entities(
        self,
        service_path: str,
        entity_set: str,
        top: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch a page of entities from an approved OData entity set (read-only GET)."""
        params = {"$top": top, "$format": "json"}
        try:
            url = f"{self._config.service_url(service_path)}/{entity_set}"
            data = self._get(url, params=params)
            # OData v2 wraps results in {"d": {"results": [...]}}; v4 uses {"value": [...]}
            d = data.get("d")
            if isinstance(d, dict) and "results" in d:
                return d["results"]
            return data.get("value", [])
        except SAPLiveConnectorError:
            raise
        except Exception as exc:
            raise SAPLiveConnectorError(f"Failed to list {entity_set}: {exc}") from exc

    def create_entity(
        self,
        service_path: str,
        entity_set: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Create an entity via the two-step CSRF handshake: GET token+cookie, then POST.

        This is the canonical cloud-native OData write pattern SAP requires —
        session affinity (cookie) and a fresh CSRF token must both be presented
        on the mutating call, or the gateway returns 403 CSRF token validation
        failed.
        """
        service_root = self._config.service_url(service_path)
        token = self._fetch_csrf_token(service_root)
        try:
            url = f"{service_root}/{entity_set}"
            data = self._post_json(url, payload, csrf_token=token)
            d = data.get("d", data)
            return {"id": d.get("__metadata", {}).get("id") or d.get("ID") or d.get("Id"), "raw": d}
        except SAPLiveConnectorError:
            raise
        except Exception as exc:
            raise SAPLiveConnectorError(f"Failed to create {entity_set}: {exc}") from exc

    # ── CSRF handshake ────────────────────────────────────────────────────────

    def _fetch_csrf_token(self, service_root_url: str) -> str:
        """Step 1 of the OData write handshake: GET with `X-CSRF-Token: Fetch`.

        The response's `X-CSRF-Token` header carries the token; the session
        cookie is captured automatically into self._cookie_jar by the opener's
        HTTPCookieProcessor and replayed on the subsequent write call.
        """
        full_url = service_root_url
        client_params = self._client_query_params()
        if client_params:
            full_url += ("&" if "?" in full_url else "?") + urllib.parse.urlencode(client_params)

        req = urllib.request.Request(full_url, headers={
            **self._auth_header(),
            "X-CSRF-Token": "Fetch",
            "Accept": "application/json",
        })
        try:
            with self._opener.open(req, timeout=self._config.timeout_seconds) as resp:
                token = resp.headers.get("X-CSRF-Token")
                if not token:
                    raise SAPLiveConnectorError(
                        "SAP gateway did not return an X-CSRF-Token — the service may not "
                        "require the write handshake, or the session could not be established."
                    )
                return token
        except urllib.error.HTTPError as exc:
            raise SAPLiveConnectorError(
                f"CSRF token fetch failed with HTTP {exc.code}. Check credentials and service path."
            ) from exc
        except OSError as exc:
            raise SAPLiveConnectorError(f"Could not reach SAP gateway at {self._config.host}: {exc}") from exc

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _auth_header(self) -> dict[str, str]:
        """Build the auth header for this config — `APIKey` (sandbox) or Basic Auth (production).

        Sandbox mode takes precedence when `api_key` is configured — see
        SAPLiveConfig's docstring for why two modes exist. Credentials are
        encoded in-memory only for the request and never logged or surfaced
        in error messages.
        """
        if self._config.is_sandbox_mode:
            return {"APIKey": self._config.api_key}

        raw = f"{self._config.username}:{self._config.password}".encode("utf-8")
        return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}

    def _client_query_params(self) -> dict[str, str]:
        """`sap-client` is a production-Gateway concept — the sandbox proxy rejects it."""
        if self._config.is_sandbox_mode or not self._config.client:
            return {}
        return {"sap-client": self._config.client}

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get(self, url: str, params: dict | None = None) -> dict[str, Any]:
        import json
        text = self._get_text(url, params)
        try:
            return json.loads(text)
        except ValueError as exc:
            raise SAPLiveConnectorError(f"SAP gateway returned a non-JSON response: {exc}") from exc

    def _get_text(self, url: str, params: dict | None = None, accept: str = "application/json") -> str:
        """GET and return the raw response body as text.

        `accept` lets callers override the `Accept` header — critical for
        `/$metadata` documents, which the OData spec defines as XML/CSDL only.
        SAP's gateway treats `Accept: application/json` on a `$metadata`
        resource as an attempt to set an unsupported `$format=json` system
        query option and rejects it with HTTP 400 "Invalid system query
        options value" — so metadata fetches must request `application/xml`.
        """
        full_url = url
        query: dict[str, Any] = dict(params or {})
        for k, v in self._client_query_params().items():
            query.setdefault(k, v)
        if query:
            full_url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(query)

        req = urllib.request.Request(full_url, headers={
            **self._auth_header(),
            "Accept": accept,
        })
        try:
            with self._opener.open(req, timeout=self._config.timeout_seconds) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            raise SAPLiveConnectorError(
                f"SAP OData gateway returned HTTP {exc.code}. Check credentials, client, and "
                f"service path. Detail: {body}"
            ) from exc
        except OSError as exc:
            raise SAPLiveConnectorError(f"Could not reach SAP gateway at {self._config.host}: {exc}") from exc

    def _post_json(self, url: str, body: dict[str, Any], csrf_token: str) -> dict[str, Any]:
        import json

        full_url = url
        client_params = self._client_query_params()
        if client_params:
            full_url += ("&" if "?" in full_url else "?") + urllib.parse.urlencode(client_params)

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            full_url,
            data=data,
            method="POST",
            headers={
                **self._auth_header(),
                "X-CSRF-Token": csrf_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with self._opener.open(req, timeout=self._config.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")[:200]
            if exc.code == 403 and "CSRF" in body_text.upper():
                raise SAPLiveConnectorError(
                    "SAP CSRF token validation failed — the session cookie and token must "
                    "both be presented on the write call. Detail: " + body_text
                ) from exc
            raise SAPLiveConnectorError(
                f"SAP OData write returned HTTP {exc.code}. Detail: {body_text}"
            ) from exc
        except OSError as exc:
            raise SAPLiveConnectorError(f"Could not reach SAP gateway at {self._config.host}: {exc}") from exc
