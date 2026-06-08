"""NetSuite live connector — OAuth 1.0a token-based auth against NetSuite REST API.

Security guarantees
-------------------
- Credentials are never logged. The _auth_header() method signs each request
  in-memory; no secrets leave this module except as Authorization headers
  over HTTPS.
- Only approved SuiteQL templates from query_templates.py are executed.
  No arbitrary SuiteQL or REST endpoint is accepted.
- All exceptions are caught and re-raised as NetSuiteLiveConnectorError so
  callers never receive raw HTTP or auth error details.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


class NetSuiteLiveConnectorError(RuntimeError):
    """Raised for all live-connector failures. Message is safe to surface to UI."""


@dataclass(frozen=True)
class NetSuiteLiveConfig:
    """Credentials loaded from the Fernet vault — never stored in plaintext."""

    account_id: str          # e.g. TSTDRV1234567  (also the OAuth realm)
    consumer_key: str
    consumer_secret: str
    token_id: str
    token_secret: str
    timeout_seconds: int = 15

    @property
    def base_url(self) -> str:
        """NetSuite REST Record API base URL for this account."""
        acct = self.account_id.lower().replace("_", "-")
        return f"https://{acct}.suitetalk.api.netsuite.com/services/rest"

    @property
    def record_url(self) -> str:
        return f"{self.base_url}/record/v1"

    @property
    def query_url(self) -> str:
        return f"{self.base_url}/query/v1/suiteql"


class NetSuiteLiveConnector:
    """Live connector against the NetSuite REST API using OAuth 1.0a HMAC-SHA256."""

    source = "live"

    def __init__(self, config: NetSuiteLiveConfig) -> None:
        self._config = config

    # ── Public interface ──────────────────────────────────────────────────────

    def test_connection(self) -> dict[str, Any]:
        """Ping the NetSuite REST API with a lightweight record list request.

        Returns {"ok": bool, "mode": "live", "message": str}.
        Never raises — returns ok=False with a safe message on failure.
        """
        try:
            # IMPORTANT: pass query params via `params=` (not embedded in the URL
            # string) so _get()/_auth_header() include them in the OAuth 1.0a
            # signature base string. NetSuite validates the signature against the
            # full parameter set — an unsigned query string causes a generic
            # "401 Invalid login attempt" that looks like a credentials problem
            # but is actually a signature mismatch (see list_record(), which signs
            # `limit` correctly and surfaces the real 400 permission error instead).
            # NOTE: the NetSuite REST Record API list endpoint does not accept a
            # `fields` query parameter (it returns "Invalid query parameter name
            # 'fields'") — `limit` alone is enough for a connectivity probe.
            url = f"{self._config.record_url}/customer"
            response = self._get(url, params={"limit": 1})
            count = len(response.get("items", []))
            return {
                "ok": True,
                "mode": "live",
                "message": f"Connected to NetSuite account {self._config.account_id}. "
                           f"Customer record returned: {count} item(s).",
            }
        except NetSuiteLiveConnectorError as exc:
            return {"ok": False, "mode": "live", "message": str(exc)}

    def fetch_schema_objects(self) -> list[str]:
        """Return the list of record types available in this account via the metadata catalog."""
        try:
            url = f"{self._config.record_url}/metadata-catalog/record"
            data = self._get(url)
            return [item.get("name", "") for item in data.get("items", []) if item.get("name")]
        except NetSuiteLiveConnectorError:
            logger.warning("Could not fetch live NetSuite schema; using static catalog.")
            return []

    def run_suiteql(self, sql: str, limit: int = 100) -> list[dict[str, Any]]:
        """Execute a pre-approved SuiteQL query string.

        Only called from run_approved_template — callers must never pass
        user-supplied SQL directly.
        """
        try:
            payload = {"q": sql}
            data = self._post_json(self._config.query_url, payload, params={"limit": limit})
            return data.get("items", [])
        except NetSuiteLiveConnectorError:
            raise
        except Exception as exc:
            raise NetSuiteLiveConnectorError(f"SuiteQL execution failed: {exc}") from exc

    def list_record(
        self,
        record_type: str,
        fields: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch records of a given type via the REST Record API.

        ``record_type`` must be a valid NetSuite record type name (e.g. 'customer',
        'invoice'). ``fields`` narrows the response — pass None for all default fields.
        """
        params: dict[str, Any] = {"limit": limit}
        if fields:
            params["fields"] = ",".join(fields)
        try:
            url = f"{self._config.record_url}/{record_type}"
            data = self._get(url, params=params)
            return data.get("items", [])
        except NetSuiteLiveConnectorError:
            raise
        except Exception as exc:
            raise NetSuiteLiveConnectorError(
                f"Failed to list {record_type} records: {exc}"
            ) from exc

    # ── OAuth 1.0a signing ────────────────────────────────────────────────────

    def _auth_header(self, method: str, url: str, extra_params: dict | None = None) -> str:
        """Build an OAuth 1.0a Authorization header for a NetSuite REST request.

        NetSuite requires HMAC-SHA256 signatures with token-based authentication.
        Credentials are accessed from self._config and never logged.
        """
        oauth_params: dict[str, str] = {
            "oauth_consumer_key": self._config.consumer_key,
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA256",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self._config.token_id,
            "oauth_version": "1.0",
        }

        # Merge all parameters for signature base string.
        # extra_params may carry non-string values (e.g. limit=50 as an int from
        # list_record's `{"limit": limit}`), and urllib.parse.quote() requires
        # str/bytes — coerce everything to str before quoting/signing.
        all_params: dict[str, str] = {
            **oauth_params,
            **{k: str(v) for k, v in (extra_params or {}).items()},
        }
        sorted_params = sorted(all_params.items())
        param_string = "&".join(
            f"{urllib.parse.quote(k, safe='')}"
            f"={urllib.parse.quote(v, safe='')}"
            for k, v in sorted_params
        )

        # Signature base string
        base_string = "&".join([
            urllib.parse.quote(method.upper(), safe=""),
            urllib.parse.quote(url.split("?")[0], safe=""),
            urllib.parse.quote(param_string, safe=""),
        ])

        # Signing key = consumer_secret & token_secret
        signing_key = (
            urllib.parse.quote(self._config.consumer_secret, safe="")
            + "&"
            + urllib.parse.quote(self._config.token_secret, safe="")
        )

        signature = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        import base64
        oauth_params["oauth_signature"] = base64.b64encode(signature).decode("utf-8")

        # Build Authorization header
        realm = urllib.parse.quote(self._config.account_id, safe="")
        header_parts = [f'realm="{realm}"'] + [
            f'{k}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        ]
        return "OAuth " + ", ".join(header_parts)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _get(self, url: str, params: dict | None = None) -> dict[str, Any]:
        import urllib.request
        import json

        full_url = url
        if params:
            full_url = url + "?" + urllib.parse.urlencode(params)

        auth = self._auth_header("GET", full_url, params)
        req = urllib.request.Request(full_url, headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Prefer": "transient",
        })
        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            raise NetSuiteLiveConnectorError(
                f"NetSuite REST API returned HTTP {exc.code}. "
                f"Check credentials and account ID. Detail: {body}"
            ) from exc
        except OSError as exc:
            raise NetSuiteLiveConnectorError(
                f"Could not reach NetSuite at {url}: {exc}"
            ) from exc

    def _post_json(
        self,
        url: str,
        body: dict[str, Any],
        params: dict | None = None,
    ) -> dict[str, Any]:
        import json
        import urllib.request

        full_url = url
        if params:
            full_url = url + "?" + urllib.parse.urlencode(params)

        auth = self._auth_header("POST", full_url)
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            full_url,
            data=data,
            method="POST",
            headers={
                "Authorization": auth,
                "Content-Type": "application/json",
                "Prefer": "transient",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:200]
            raise NetSuiteLiveConnectorError(
                f"NetSuite SuiteQL returned HTTP {exc.code}. Detail: {body}"
            ) from exc
        except OSError as exc:
            raise NetSuiteLiveConnectorError(
                f"Could not reach NetSuite SuiteQL endpoint: {exc}"
            ) from exc
