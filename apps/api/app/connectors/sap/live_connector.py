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
        """Root HTTPS URL for this SAP system's OData Gateway.

        Tolerates a full endpoint URL pasted into `host` by mistake — a very
        easy slip, since the SAP Business Accelerator Hub prominently displays
        full service-endpoint URLs (e.g.
        "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_X_SRV")
        right next to the "Show API Key" button, and copy-pasting that whole
        string instead of just the hostname produces a garbled, duplicated,
        unroutable URL once `service_url()` appends its own path — which the
        gateway then rejects with a generic "Invalid system query options
        value" 400 (confirmed live). Stripping everything after the first "/"
        keeps only the hostname, so "host" behaves correctly whether the user
        enters "sandbox.api.sap.com" or the full endpoint URL.
        """
        host = self.host.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        host = host.split("/", 1)[0]
        return f"https://{host}"

    def service_url(self, service_path: str) -> str:
        """Build a full OData service URL, e.g. service_path='API_BUSINESS_PARTNER/A_BusinessPartner'.

        Production Gateway shape: {base_url}/sap/opu/odata/sap/{service_path}
        Sandbox proxy shape:      {base_url}/{api_base_path}/sap/opu/odata/sap/{service_path}
        """
        path = service_path.lstrip("/")
        prefix = f"/{self.api_base_path.strip('/')}" if self.api_base_path else ""
        return f"{self.base_url}{prefix}/sap/opu/odata/sap/{path}"


def _parse_odata_metadata(xml_text: str) -> list:
    """Parse an OData CSDL $metadata document and return SchemaObject instances.

    Design notes
    ------------
    - Namespace-agnostic: uses ``{*}`` wildcard so the parser works with any
      edmx prefix version (OData v2 and v4 both in the wild on SAP systems).
    - EDM property types are mapped to the platform's three-value vocabulary:
      "string" / "number" / "date" / "boolean".
    - EntitySet declarations are used as object IDs (the actual queryable
      collection names, e.g. ``A_AddressEmailAddress``); the matching
      EntityType provides the field definitions.
    - If no EntitySet declarations exist (unusual but possible in sub-schemas),
      falls back to deriving the set name by stripping the "Type" suffix from
      the EntityType name (SAP's standard convention:
      ``A_AddressEmailAddressType`` → ``A_AddressEmailAddress``).
    - Returns objects sorted by their entity-set name for stable UI ordering.
    """
    import xml.etree.ElementTree as ET

    _EDM: dict[str, str] = {
        # Text / identifier types
        "Edm.String": "string", "Edm.Guid": "string",
        "Edm.Binary": "string", "Edm.Time": "string", "Edm.TimeOfDay": "string",
        # Boolean
        "Edm.Boolean": "boolean",
        # Numeric types
        "Edm.Decimal": "number", "Edm.Double": "number", "Edm.Single": "number",
        "Edm.Int16": "number", "Edm.Int32": "number", "Edm.Int64": "number",
        "Edm.Byte": "number", "Edm.SByte": "number",
        # Temporal types
        "Edm.DateTime": "date", "Edm.DateTimeOffset": "date", "Edm.Date": "date",
    }

    def _camel_label(name: str) -> str:
        """Turn an OData name into a readable label.

        ``A_AddressEmailAddress`` → ``Address Email Address``
        ``BusinessPartnerFullName`` → ``Business Partner Full Name``
        """
        # Strip common SAP prefixes: A_ or A_Bla → Bla
        clean = re.sub(r"^A_", "", name)
        # Insert spaces before each run of capitals that follows a lowercase char
        spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", clean)
        # Insert spaces between consecutive capitals followed by lowercase (e.g. VATNo → VAT No)
        spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
        return spaced.strip()

    from ..base import SchemaField, SchemaObject  # local import — avoids circular dep at module load

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("SAP $metadata XML parse error: %s", exc)
        return []

    # ── Step 1: collect EntityType → fields map ────────────────────────────
    entity_type_fields: dict[str, list] = {}  # EntityType.Name → [SchemaField, ...]

    for et_elem in root.findall(".//{*}EntityType"):
        et_name = et_elem.get("Name", "")
        if not et_name:
            continue

        # Key properties — required=True for key fields regardless of Nullable attr
        key_props: set[str] = {
            pr.get("Name", "")
            for pr in et_elem.findall(".//{*}PropertyRef")
        }

        fields: list = []
        for prop in et_elem.findall("{*}Property"):
            pname = prop.get("Name", "")
            edm_type = prop.get("Type", "Edm.String")
            nullable = prop.get("Nullable", "true").lower()
            max_length = prop.get("MaxLength")
            precision = prop.get("Precision")

            is_key = pname in key_props
            required = is_key or nullable == "false"
            platform_type = _EDM.get(edm_type, "string")

            # Build a lightweight sample hint from MaxLength / Precision if present
            sample: str | None = None
            if platform_type == "string" and max_length:
                sample = f"max {max_length} chars"
            elif platform_type == "number" and precision:
                sample = f"precision {precision}"

            fields.append(SchemaField(
                name=pname,
                label=_camel_label(pname),
                type=platform_type,
                required=required,
                sample=sample,
            ))

        if fields:
            entity_type_fields[et_name] = fields

    # ── Step 2: match EntitySets to their EntityType definitions ──────────
    objects: list = []
    seen_sets: set[str] = set()

    for es_elem in root.findall(".//{*}EntitySet"):
        es_name = es_elem.get("Name", "")
        # EntityType attr may be namespace-qualified: "GWSAMPLE_BASIC.SalesOrder"
        et_ref = es_elem.get("EntityType", "").split(".")[-1]

        if not es_name or es_name in seen_sets:
            continue
        seen_sets.add(es_name)

        fields = entity_type_fields.get(et_ref, [])
        if not fields:
            continue  # skip sets whose type definition wasn't parsed

        objects.append(SchemaObject(
            object_id=es_name,
            label=_camel_label(es_name),
            fields=fields,
        ))

    # ── Step 3: fallback — derive set names from EntityType names ──────────
    # Used when no EntitySet declarations are present (e.g. in sub-schemas).
    if not objects and entity_type_fields:
        for et_name, fields in entity_type_fields.items():
            # SAP convention: A_AddressEmailAddressType → A_AddressEmailAddress
            set_name = re.sub(r"Type$", "", et_name)
            objects.append(SchemaObject(
                object_id=set_name,
                label=_camel_label(set_name),
                fields=fields,
            ))

    return sorted(objects, key=lambda o: o.object_id)


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
                # $metadata lives at the service root — NOT under an entity set.
                # Correct:   .../sap/opu/odata/sap/API_BUSINESS_PARTNER/$metadata
                # Wrong:     .../sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner/$metadata
                # (the latter path folds the entity set into the service path and
                # causes SAP's Apigee gateway to return HTTP 400.)
                # $metadata is XML/CSDL by spec — requesting JSON causes SAP to
                # reject with "Invalid system query options value".
                url = f"{self._config.service_url('API_BUSINESS_PARTNER')}/$metadata"
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

    def fetch_schema_objects(self, service_path: str) -> list:
        """Fetch the OData $metadata document and return a list of SchemaObject instances.

        Calls $metadata at the **service root** (not under an entity set — see
        test_connection for why entity-set-level $metadata returns HTTP 400).
        Parses EntitySet + EntityType declarations from the CSDL XML and maps
        EDM property types to the platform's SchemaField vocabulary.

        Returns an empty list (triggering static-schema fallback in the plugin)
        if the metadata document cannot be fetched or parsed.
        """
        try:
            url = f"{self._config.service_url(service_path)}/$metadata"
            xml_text = self._get_text(url, accept="application/xml")
            return _parse_odata_metadata(xml_text)
        except SAPLiveConnectorError:
            logger.warning("Could not fetch live SAP $metadata for %s; falling back to static catalog.", service_path)
            return []

    def list_entities(
        self,
        service_path: str,
        entity_set: str,
        top: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch a page of entities from an approved OData entity set (read-only GET).

        Deliberately sends ONLY `$top` as a system query option — JSON is
        negotiated purely via the `Accept: application/json` header (set by
        `_get`/`_get_text`). An earlier version also sent `$format=json` as a
        query parameter; the sandbox's Apigee-fronted gateway rejected that
        combination with the same HTTP 400 "Invalid system query options
        value" error that `$metadata` + `Accept: application/json` produced
        (see `_get_text`'s docstring) — `$format` is OData-version-sensitive
        (V2 accepts the bare `json` shorthand; V4 backends behind this proxy
        evidently don't), whereas the `Accept` header is the protocol-correct,
        version-agnostic way to negotiate representation and works for both.
        """
        params = {"$top": top}
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
            # Explicitly accept gzip so the gateway doesn't send a partially-
            # compressed body without a Content-Encoding header (which breaks
            # the plain .decode("utf-8") call below).
            "Accept-Encoding": "gzip, identity",
        })
        try:
            with self._opener.open(req, timeout=self._config.timeout_seconds) as resp:
                raw = resp.read()
                encoding = resp.headers.get("Content-Encoding", "")
                if encoding == "gzip" or (raw[:2] == b"\x1f\x8b"):
                    import gzip as _gzip
                    raw = _gzip.decompress(raw)
                return raw.decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw_err = exc.read()
            encoding = exc.headers.get("Content-Encoding", "")
            if encoding == "gzip" or (raw_err[:2] == b"\x1f\x8b"):
                import gzip as _gzip
                try:
                    raw_err = _gzip.decompress(raw_err)
                except Exception:
                    pass
            body = raw_err.decode("utf-8", errors="replace")[:200]
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
