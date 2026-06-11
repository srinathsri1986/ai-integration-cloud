"""Schema discovery service — R18a.

Probes a REST API endpoint and infers the field schema from the JSON response,
or parses an OpenAPI 3.x specification to extract request/response schemas.

Security notes:
- Timeouts are hard-capped at 5 seconds — no indefinite blocking.
- Nested recursion depth is capped at 4 — prevents stack exhaustion on
  pathological responses.
- No credential values are logged; only status codes and field counts.
- SSRF protection is the infra layer's responsibility; this service accepts
  any URL supplied by an authenticated tenant.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

_DISCOVERY_TIMEOUT_S = 5.0
_MAX_DEPTH = 4
_MAX_FIELDS = 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, str):
        # Heuristic date detection
        if re.match(r"^\d{4}-\d{2}-\d{2}", value):
            return "date"
    return "string"


def _flatten(obj: Any, prefix: str = "", depth: int = 0) -> list[dict]:
    """Recursively flatten a JSON object into a list of FieldInfo dicts."""
    if depth > _MAX_DEPTH or not isinstance(obj, dict):
        return []

    fields: list[dict] = []
    for key, value in obj.items():
        if len(fields) >= _MAX_FIELDS:
            break
        path = f"{prefix}.{key}" if prefix else key
        ftype = _infer_type(value)
        sample = None
        if ftype not in ("object", "array") and value is not None:
            sample = str(value)[:120]
        label = key.replace("_", " ").replace("-", " ").title()
        fields.append({
            "name": path,
            "label": label,
            "type": ftype,
            "required": False,
            "sample": sample,
        })
        # Recurse into objects (not arrays — too variable)
        if ftype == "object":
            fields.extend(_flatten(value, prefix=path, depth=depth + 1))
    return fields


def _unwrap_envelope(data: Any) -> Any:
    """Unwrap common API envelope patterns: {data: [...], items: [...], etc.}"""
    if isinstance(data, list):
        return data[0] if data else {}
    if isinstance(data, dict):
        for key in ("data", "items", "results", "records", "objects", "value", "content"):
            candidate = data.get(key)
            if isinstance(candidate, list) and candidate:
                return candidate[0]
            if isinstance(candidate, dict):
                return candidate
    return data


# ---------------------------------------------------------------------------
# OpenAPI 3.x helpers
# ---------------------------------------------------------------------------

def _fields_from_openapi_schema(schema: dict, name: str = "", depth: int = 0) -> list[dict]:
    """Recursively extract FieldInfo dicts from an OpenAPI schema object."""
    if depth > _MAX_DEPTH:
        return []

    fields: list[dict] = []
    properties = schema.get("properties", {})
    required_set = set(schema.get("required", []))

    for prop, prop_schema in properties.items():
        if len(fields) >= _MAX_FIELDS:
            break
        path = f"{name}.{prop}" if name else prop
        prop_type = prop_schema.get("type", "string")
        # Normalise OpenAPI types → our types
        type_map = {
            "integer": "number", "float": "number", "double": "number",
            "object": "object", "array": "array", "boolean": "boolean",
        }
        ftype = type_map.get(prop_type, "string")
        # Override with "date" for string+format:date / date-time
        if prop_type == "string" and prop_schema.get("format", "").startswith("date"):
            ftype = "date"

        example = prop_schema.get("example") or prop_schema.get("default")
        fields.append({
            "name": path,
            "label": prop.replace("_", " ").replace("-", " ").title(),
            "type": ftype,
            "required": prop in required_set,
            "sample": str(example)[:120] if example is not None else None,
        })
        if ftype == "object":
            fields.extend(_fields_from_openapi_schema(prop_schema, path, depth + 1))

    return fields


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class SchemaDiscoveryService:

    # --- Live endpoint probe --------------------------------------------------

    def probe_endpoint(
        self,
        base_url: str,
        path: str,
        auth_headers: dict[str, str],
        method: str = "GET",
    ) -> tuple[list[dict], list[str]]:
        """Probe *base_url + path*, parse the JSON response, return (fields, warnings)."""
        import httpx

        url = base_url.rstrip("/") + "/" + path.lstrip("/")
        warnings: list[str] = []
        t0 = time.monotonic()

        try:
            with httpx.Client(timeout=_DISCOVERY_TIMEOUT_S, follow_redirects=True) as client:
                resp = client.request(method, url, headers={**auth_headers, "Accept": "application/json"})
        except httpx.TimeoutException:
            raise ValueError(f"Endpoint timed out after {_DISCOVERY_TIMEOUT_S}s — check URL and auth.")
        except httpx.RequestError as exc:
            raise ValueError(f"Could not reach endpoint: {exc}")

        latency = int((time.monotonic() - t0) * 1000)
        logger.info("Schema probe %s %s → %s in %dms", method, url, resp.status_code, latency)

        if resp.status_code == 401:
            raise ValueError("Authentication failed (401). Check credentials.")
        if resp.status_code == 403:
            raise ValueError("Forbidden (403). Check API key permissions.")
        if resp.status_code >= 400:
            raise ValueError(f"Endpoint returned {resp.status_code}. Check URL and path.")

        try:
            data = resp.json()
        except Exception:
            raise ValueError("Response is not valid JSON — cannot infer schema.")

        sample = _unwrap_envelope(data)
        if not isinstance(sample, dict):
            warnings.append(
                "Response root is not a JSON object — schema may be incomplete. "
                "Try a path that returns a single record."
            )
            return [], warnings

        fields = _flatten(sample)
        if not fields:
            warnings.append("No fields discovered — the response object appears to be empty.")
        return fields, warnings

    # --- OpenAPI spec parse ---------------------------------------------------

    def parse_openapi_url(
        self,
        openapi_url: str,
        schema_name: str | None = None,
    ) -> tuple[list[dict], list[str]]:
        """Fetch and parse an OpenAPI 3.x spec, return (fields, warnings)."""
        import httpx

        warnings: list[str] = []
        try:
            with httpx.Client(timeout=_DISCOVERY_TIMEOUT_S) as client:
                resp = client.get(openapi_url, headers={"Accept": "application/json, application/yaml"})
                resp.raise_for_status()
        except Exception as exc:
            raise ValueError(f"Could not fetch OpenAPI spec: {exc}")

        content_type = resp.headers.get("content-type", "")
        if "yaml" in content_type or openapi_url.endswith((".yaml", ".yml")):
            try:
                import yaml  # type: ignore[import]
                spec = yaml.safe_load(resp.text)
            except Exception:
                raise ValueError("Could not parse YAML OpenAPI spec.")
        else:
            try:
                spec = resp.json()
            except Exception:
                raise ValueError("Could not parse JSON OpenAPI spec.")

        components = spec.get("components", {}).get("schemas", {})
        if not components:
            # Swagger 2.0 fallback
            components = spec.get("definitions", {})

        if schema_name and schema_name in components:
            schema = components[schema_name]
        elif components:
            # Pick the first schema in the spec
            schema_name, schema = next(iter(components.items()))
            warnings.append(f"No schema_name specified — using first schema: '{schema_name}'.")
        else:
            raise ValueError("OpenAPI spec contains no component schemas.")

        # Dereference $ref
        schema = self._deref(schema, components)
        fields = _fields_from_openapi_schema(schema)
        if not fields:
            warnings.append("Schema has no properties — no fields discovered.")
        return fields, warnings

    def _deref(self, schema: dict, components: dict) -> dict:
        """Shallow $ref resolution (one level)."""
        if "$ref" in schema:
            ref = schema["$ref"]
            name = ref.split("/")[-1]
            return components.get(name, {})
        return schema


schema_discovery_service = SchemaDiscoveryService()
