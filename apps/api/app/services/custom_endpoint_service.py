"""Custom endpoint service — R18a.

CRUD and credential management for user-defined REST API endpoints.
Credentials are encrypted via credential_service (Fernet AES-128) and stored
in connector_config_records with connector_id = "custom:{endpoint_id}".
The custom_endpoints table stores only safe metadata.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import UTC, datetime as _dt
from typing import Any

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.custom_endpoint import (
    CustomEndpoint,
    CustomEndpointCreateRequest,
    CustomEndpointUpdateRequest,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
    ConnectionTestResponse,
)
from app.services.credential_service import credential_service
from app.services.schema_discovery import schema_discovery_service

logger = logging.getLogger(__name__)

_ID_SAFE = re.compile(r"[^a-z0-9-]")


def _slugify(name: str) -> str:
    base = name.lower().strip().replace(" ", "-")
    base = _ID_SAFE.sub("", base)[:48]
    return base or "custom"


class CustomEndpointService:

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _now(self) -> str:
        return _dt.now(UTC).isoformat()

    def _get_row(self, endpoint_id: str, tenant_id: int | None) -> dict | None:
        with SessionLocal() as session:
            row = session.execute(
                text(
                    "SELECT * FROM custom_endpoints "
                    "WHERE id = :id AND (tenant_id = :tid OR (tenant_id IS NULL AND :tid IS NULL))"
                ),
                {"id": endpoint_id, "tid": tenant_id},
            ).fetchone()
        if not row:
            return None
        return dict(row._mapping)

    def _build_endpoint(self, row: dict, has_credentials: bool) -> CustomEndpoint:
        row["has_credentials"] = has_credentials
        return CustomEndpoint.from_row(row)

    # ------------------------------------------------------------------
    # Auth header builder
    # ------------------------------------------------------------------

    def _auth_headers(self, endpoint_id: str, tenant_id: int | None) -> dict[str, str]:
        """Return HTTP headers required to authenticate against the endpoint."""
        connector_key = f"custom:{endpoint_id}"
        creds = credential_service.get_credentials(connector_key, tenant_id)
        if not creds:
            return {}
        scheme = creds.get("auth_scheme", "none")
        if scheme == "api_key":
            header_name = creds.get("auth_header_name", "X-API-Key")
            return {header_name: creds.get("api_key", "")}
        if scheme == "bearer":
            return {"Authorization": f"Bearer {creds.get('bearer_token', '')}"}
        if scheme == "basic":
            import base64
            pair = f"{creds.get('username','')}:{creds.get('password','')}".encode()
            token = base64.b64encode(pair).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    def _store_credentials(
        self, endpoint_id: str, request: CustomEndpointCreateRequest | CustomEndpointUpdateRequest, tenant_id: int | None
    ) -> None:
        creds: dict[str, Any] = {"auth_scheme": request.auth_scheme if hasattr(request, "auth_scheme") else "none"}
        if hasattr(request, "api_key") and request.api_key:
            creds["api_key"] = request.api_key
        if hasattr(request, "bearer_token") and request.bearer_token:
            creds["bearer_token"] = request.bearer_token
        if hasattr(request, "username") and request.username:
            creds["username"] = request.username
        if hasattr(request, "password") and request.password:
            creds["password"] = request.password
        if len(creds) > 1:  # more than just auth_scheme
            connector_key = f"custom:{endpoint_id}"
            credential_service.store_credentials(connector_key, creds, tenant_id=tenant_id)
            logger.info("Stored credentials for custom endpoint %s tenant=%s", endpoint_id, tenant_id)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, request: CustomEndpointCreateRequest, tenant_id: int | None = None) -> CustomEndpoint:
        now = self._now()
        # Generate a unique ID from the name
        base_slug = _slugify(request.name)
        endpoint_id = f"{base_slug}-{now[-6:].replace(':', '').replace('-', '').replace('+', '').replace('.', '')}"

        with SessionLocal() as session:
            session.execute(
                text(
                    "INSERT INTO custom_endpoints "
                    "(id, tenant_id, name, description, base_url, auth_scheme, "
                    " default_path, http_method, field_schema, created_at, updated_at) "
                    "VALUES (:id, :tid, :name, :desc, :base_url, :auth_scheme, "
                    "        :path, :method, :schema, :now, :now)"
                ),
                {
                    "id": endpoint_id,
                    "tid": tenant_id,
                    "name": request.name,
                    "desc": request.description,
                    "base_url": str(request.base_url),
                    "auth_scheme": request.auth_scheme,
                    "path": request.default_path,
                    "method": request.http_method,
                    "schema": "[]",
                    "now": now,
                },
            )
            session.commit()

        # Store credentials encrypted (separate from the endpoint row)
        self._store_credentials(endpoint_id, request, tenant_id)

        row = self._get_row(endpoint_id, tenant_id)
        has_creds = bool(credential_service.get_credentials(f"custom:{endpoint_id}", tenant_id))
        return self._build_endpoint(row, has_creds)

    def list(self, tenant_id: int | None = None) -> list[CustomEndpoint]:
        with SessionLocal() as session:
            if tenant_id is not None:
                rows = session.execute(
                    text("SELECT * FROM custom_endpoints WHERE tenant_id = :tid OR tenant_id IS NULL ORDER BY name"),
                    {"tid": tenant_id},
                ).fetchall()
            else:
                rows = session.execute(
                    text("SELECT * FROM custom_endpoints WHERE tenant_id IS NULL ORDER BY name")
                ).fetchall()

        result = []
        for row in rows:
            d = dict(row._mapping)
            has_creds = bool(credential_service.get_credentials(f"custom:{d['id']}", tenant_id))
            result.append(self._build_endpoint(d, has_creds))
        return result

    def get(self, endpoint_id: str, tenant_id: int | None = None) -> CustomEndpoint:
        row = self._get_row(endpoint_id, tenant_id)
        if not row:
            raise KeyError(f"Custom endpoint '{endpoint_id}' not found.")
        has_creds = bool(credential_service.get_credentials(f"custom:{endpoint_id}", tenant_id))
        return self._build_endpoint(row, has_creds)

    def update(self, endpoint_id: str, request: CustomEndpointUpdateRequest, tenant_id: int | None = None) -> CustomEndpoint:
        row = self._get_row(endpoint_id, tenant_id)
        if not row:
            raise KeyError(f"Custom endpoint '{endpoint_id}' not found.")

        updates: dict[str, Any] = {"now": self._now(), "id": endpoint_id}
        set_parts: list[str] = ["updated_at = :now"]

        if request.name is not None:
            set_parts.append("name = :name")
            updates["name"] = request.name
        if request.description is not None:
            set_parts.append("description = :desc")
            updates["desc"] = request.description
        if request.default_path is not None:
            set_parts.append("default_path = :path")
            updates["path"] = request.default_path
        if request.http_method is not None:
            set_parts.append("http_method = :method")
            updates["method"] = request.http_method

        if set_parts:
            with SessionLocal() as session:
                session.execute(
                    text(f"UPDATE custom_endpoints SET {', '.join(set_parts)} WHERE id = :id"),
                    updates,
                )
                session.commit()

        # Update credentials if provided
        self._store_credentials(endpoint_id, request, tenant_id)

        return self.get(endpoint_id, tenant_id)

    def delete(self, endpoint_id: str, tenant_id: int | None = None) -> None:
        row = self._get_row(endpoint_id, tenant_id)
        if not row:
            raise KeyError(f"Custom endpoint '{endpoint_id}' not found.")
        with SessionLocal() as session:
            session.execute(
                text("DELETE FROM custom_endpoints WHERE id = :id"), {"id": endpoint_id}
            )
            session.commit()
        # Also revoke stored credentials
        try:
            credential_service.revoke_token(f"custom:{endpoint_id}", tenant_id)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Schema discovery
    # ------------------------------------------------------------------

    def discover_schema(
        self, endpoint_id: str, request: SchemaDiscoveryRequest, tenant_id: int | None = None
    ) -> SchemaDiscoveryResponse:
        row = self._get_row(endpoint_id, tenant_id)
        if not row:
            raise KeyError(f"Custom endpoint '{endpoint_id}' not found.")

        auth_headers = self._auth_headers(endpoint_id, tenant_id)
        warnings: list[str] = []
        method = "openapi" if request.openapi_url else "probe"

        if request.openapi_url:
            fields, warnings = schema_discovery_service.parse_openapi_url(
                request.openapi_url,
                schema_name=request.openapi_schema_name,
            )
        else:
            path = request.path or row.get("default_path", "/")
            fields, warnings = schema_discovery_service.probe_endpoint(
                base_url=row["base_url"],
                path=path,
                auth_headers=auth_headers,
                method=row.get("http_method", "GET"),
            )

        # Persist discovered schema
        now = self._now()
        with SessionLocal() as session:
            session.execute(
                text(
                    "UPDATE custom_endpoints SET field_schema = :schema, updated_at = :now WHERE id = :id"
                ),
                {"schema": json.dumps([f.model_dump() for f in fields] if fields else [f if isinstance(f, dict) else f for f in fields]),
                 "now": now,
                 "id": endpoint_id},
            )
            session.commit()

        # Normalise to FieldInfo objects
        from app.models.custom_endpoint import FieldInfo
        field_objs = [FieldInfo(**f) if isinstance(f, dict) else f for f in fields]

        return SchemaDiscoveryResponse(
            endpointId=endpoint_id,
            fields=field_objs,
            fieldCount=len(field_objs),
            discoveryMethod=method,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    def test_connection(self, endpoint_id: str, tenant_id: int | None = None) -> ConnectionTestResponse:
        import httpx

        row = self._get_row(endpoint_id, tenant_id)
        if not row:
            raise KeyError(f"Custom endpoint '{endpoint_id}' not found.")

        auth_headers = self._auth_headers(endpoint_id, tenant_id)
        url = row["base_url"].rstrip("/") + "/" + row.get("default_path", "/").lstrip("/")
        t0 = time.monotonic()

        try:
            with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                resp = client.request(
                    row.get("http_method", "GET"),
                    url,
                    headers={**auth_headers, "Accept": "application/json"},
                )
            latency = int((time.monotonic() - t0) * 1000)
            ok = resp.status_code < 400
            return ConnectionTestResponse(
                ok=ok,
                statusCode=resp.status_code,
                message=f"HTTP {resp.status_code}" if ok else f"HTTP {resp.status_code} — check credentials and URL.",
                latencyMs=latency,
            )
        except httpx.TimeoutException:
            latency = int((time.monotonic() - t0) * 1000)
            return ConnectionTestResponse(
                ok=False, statusCode=None,
                message="Request timed out — check the URL and network access.",
                latencyMs=latency,
            )
        except Exception as exc:
            latency = int((time.monotonic() - t0) * 1000)
            return ConnectionTestResponse(
                ok=False, statusCode=None,
                message=f"Connection failed: {exc}",
                latencyMs=latency,
            )

    # ------------------------------------------------------------------
    # Schema accessor (used by flow execution and wizard)
    # ------------------------------------------------------------------

    def get_field_schema(self, endpoint_id: str, tenant_id: int | None = None) -> list[dict]:
        """Return the stored field schema as a plain list of dicts."""
        row = self._get_row(endpoint_id, tenant_id)
        if not row:
            return []
        raw = row.get("field_schema", "[]")
        return json.loads(raw) if isinstance(raw, str) else (raw or [])


custom_endpoint_service = CustomEndpointService()
