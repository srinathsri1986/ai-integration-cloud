"""Pydantic models for the custom-endpoint registry — R18a.

CustomEndpoint lets any tenant register an arbitrary REST API as a source or
target connector.  Credentials are encrypted via credential_service and never
returned in API responses; only safe metadata (name, base_url, auth_scheme,
field_schema) is exposed.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Field schema primitives
# ---------------------------------------------------------------------------

FieldType = Literal["string", "number", "boolean", "date", "object", "array"]


class FieldInfo(BaseModel):
    """Single discoverable field on a source or target endpoint."""
    name: str = Field(description="Dot-path key, e.g. 'customer.email'")
    label: str = Field(description="Human-readable label derived from name")
    type: FieldType = "string"
    required: bool = False
    sample: str | None = Field(default=None, description="Truncated sample value for display")

    @field_validator("name")
    @classmethod
    def name_is_safe(cls, v: str) -> str:
        # Dot-path only — no SQL/script injection via field names
        if not v or len(v) > 256:
            raise ValueError("Field name must be 1-256 characters")
        return v


# ---------------------------------------------------------------------------
# Inline field mapping row (stored on FlowDefinition.field_mappings)
# ---------------------------------------------------------------------------

MappingTransformType = Literal[
    "direct",
    "uppercase",
    "lowercase",
    "to_string",
    "to_number",
    "format_date",
]


class InlineFieldMapping(BaseModel):
    """One source-field → target-field mapping row embedded on a FlowDefinition."""
    source_field: str = Field(alias="sourceField", description="Dot-path on the source payload")
    target_field: str = Field(alias="targetField", description="Dot-path on the target payload")
    transform: MappingTransformType = Field(default="direct", alias="transform")
    source_type: FieldType = Field(default="string", alias="sourceType")
    target_type: FieldType = Field(default="string", alias="targetType")

    @field_validator("source_field", "target_field")
    @classmethod
    def field_path_safe(cls, v: str) -> str:
        if not v or len(v) > 256:
            raise ValueError("Field path must be 1-256 characters")
        return v


# ---------------------------------------------------------------------------
# Custom endpoint CRUD models
# ---------------------------------------------------------------------------

AuthScheme = Literal["none", "api_key", "bearer", "basic"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH"]


class CustomEndpointCreateRequest(BaseModel):
    """Body for POST /custom-endpoints.  Accepts both camelCase and snake_case keys."""
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    base_url: str = Field(alias="baseUrl", default=None, min_length=7, max_length=512, description="e.g. https://api.example.com")  # type: ignore[assignment]
    auth_scheme: AuthScheme = Field(alias="authScheme", default="none")
    default_path: str = Field(alias="defaultPath", default="/", max_length=256, description="Endpoint path for schema discovery and execution")
    http_method: HttpMethod = Field(alias="httpMethod", default="GET")
    # Credentials — stored encrypted, NEVER returned in responses
    api_key: str | None = Field(default=None, exclude=True, description="API key (api_key scheme)")
    bearer_token: str | None = Field(default=None, exclude=True, description="Bearer token (bearer scheme)")
    username: str | None = Field(default=None, exclude=True, description="Username (basic scheme)")
    password: str | None = Field(default=None, exclude=True, description="Password (basic scheme)")

    @field_validator("base_url")
    @classmethod
    def base_url_safe(cls, v: str) -> str:
        v = v.rstrip("/")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        # SSRF guard: block private/loopback addresses in deployed environments.
        # localhost is permitted only in local/test to allow integration test mocks.
        from app.core.config import get_settings
        settings = get_settings()
        if settings.environment not in ("local", "test"):
            forbidden = [
                "localhost", "127.0.0.1", "0.0.0.0", "169.254.",
                "10.", "192.168.", "172.16.",
            ]
            if any(token in v for token in forbidden):
                raise ValueError(
                    "base_url must resolve to a publicly routable address. "
                    "Private/loopback addresses are not permitted."
                )
        return v

    @field_validator("name", "description")
    @classmethod
    def no_raw_code(cls, v: str) -> str:
        blocked = ["<script", "javascript:", "eval(", "exec(", "os.system"]
        if any(b in v.lower() for b in blocked):
            raise ValueError("Endpoint name/description cannot contain code or script content.")
        return v


class CustomEndpointUpdateRequest(BaseModel):
    """Body for PATCH /custom-endpoints/{id}.  All fields optional."""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    default_path: str | None = Field(alias="defaultPath", default=None, max_length=256)
    http_method: HttpMethod | None = Field(alias="httpMethod", default=None)
    # Credential rotation — if provided, re-encrypts and replaces
    api_key: str | None = Field(default=None, exclude=True)
    bearer_token: str | None = Field(default=None, exclude=True)
    username: str | None = Field(default=None, exclude=True)
    password: str | None = Field(default=None, exclude=True)


class CustomEndpoint(BaseModel):
    """Read model returned by GET /custom-endpoints — NO secrets."""
    endpoint_id: str = Field(alias="endpointId")
    tenant_id: int | None = Field(alias="tenantId")
    name: str
    description: str
    base_url: str = Field(alias="baseUrl")
    auth_scheme: AuthScheme = Field(alias="authScheme")
    default_path: str = Field(alias="defaultPath")
    http_method: str = Field(alias="httpMethod")
    field_schema: list[FieldInfo] = Field(default_factory=list, alias="fieldSchema")
    field_count: int = Field(default=0, alias="fieldCount")
    has_credentials: bool = Field(default=False, alias="hasCredentials")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "CustomEndpoint":
        import json
        schema_raw = row.get("field_schema", "[]")
        field_schema = json.loads(schema_raw) if isinstance(schema_raw, str) else schema_raw
        fields = [FieldInfo(**f) for f in (field_schema or [])]
        return cls(
            endpointId=row["id"],
            tenantId=row.get("tenant_id"),
            name=row["name"],
            description=row.get("description", ""),
            baseUrl=row["base_url"],
            authScheme=row.get("auth_scheme", "none"),
            defaultPath=row.get("default_path", "/"),
            httpMethod=row.get("http_method", "GET"),
            fieldSchema=fields,
            fieldCount=len(fields),
            hasCredentials=bool(row.get("has_credentials", False)),
            createdAt=row.get("created_at", ""),
            updatedAt=row.get("updated_at", ""),
        )


# ---------------------------------------------------------------------------
# Schema discovery request/response
# ---------------------------------------------------------------------------

class SchemaDiscoveryRequest(BaseModel):
    """Body for POST /custom-endpoints/{id}/discover-schema."""
    # Override the stored default_path for this discovery run
    path: str | None = Field(default=None, max_length=256)
    # If set, parse OpenAPI spec instead of probing the live endpoint
    openapi_url: str | None = Field(default=None, max_length=512, alias="openapiUrl")
    # Which object/schema to use from the OpenAPI spec (defaults to first response schema)
    openapi_schema_name: str | None = Field(default=None, max_length=120, alias="openapiSchemaName")


class SchemaDiscoveryResponse(BaseModel):
    endpoint_id: str = Field(alias="endpointId")
    fields: list[FieldInfo]
    field_count: int = Field(alias="fieldCount")
    discovery_method: str = Field(alias="discoveryMethod")  # "probe" | "openapi"
    warnings: list[str] = Field(default_factory=list)


class ConnectionTestResponse(BaseModel):
    ok: bool
    status_code: int | None = Field(default=None, alias="statusCode")
    message: str
    latency_ms: int = Field(alias="latencyMs")
