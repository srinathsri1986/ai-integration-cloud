"""Custom endpoint API — R18a.

Routes for managing user-defined REST API endpoints that can act as source or
target in any flow integration.  Each tenant can register their own APIs with
their own credentials (encrypted, never returned in responses).

All routes require integration:read / integration:write permissions via the
same RBAC middleware used by the flows and connectors APIs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import require_permissions
from app.models.custom_endpoint import (
    ConnectionTestResponse,
    CustomEndpoint,
    CustomEndpointCreateRequest,
    CustomEndpointUpdateRequest,
    SchemaDiscoveryRequest,
    SchemaDiscoveryResponse,
)
from app.services.custom_endpoint_service import custom_endpoint_service

router = APIRouter(prefix="/api/v1/custom-endpoints", tags=["custom-endpoints"])


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=CustomEndpoint, status_code=status.HTTP_201_CREATED)
def create_custom_endpoint(
    body: CustomEndpointCreateRequest,
    user=Depends(require_permissions("integration:write")),
) -> CustomEndpoint:
    """Register a new REST API as a source or target connector."""
    return custom_endpoint_service.create(body, tenant_id=user.tenant_id)


@router.get("", response_model=list[CustomEndpoint])
def list_custom_endpoints(
    user=Depends(require_permissions("integration:read")),
) -> list[CustomEndpoint]:
    """List all custom endpoints for the calling tenant."""
    return custom_endpoint_service.list(tenant_id=user.tenant_id)


@router.get("/{endpoint_id}", response_model=CustomEndpoint)
def get_custom_endpoint(
    endpoint_id: str,
    user=Depends(require_permissions("integration:read")),
) -> CustomEndpoint:
    try:
        return custom_endpoint_service.get(endpoint_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{endpoint_id}", response_model=CustomEndpoint)
def update_custom_endpoint(
    endpoint_id: str,
    body: CustomEndpointUpdateRequest,
    user=Depends(require_permissions("integration:write")),
) -> CustomEndpoint:
    """Update endpoint metadata or rotate credentials."""
    try:
        return custom_endpoint_service.update(endpoint_id, body, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_endpoint(
    endpoint_id: str,
    user=Depends(require_permissions("integration:write")),
) -> None:
    """Remove a custom endpoint and revoke its stored credentials."""
    try:
        custom_endpoint_service.delete(endpoint_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Schema discovery
# ---------------------------------------------------------------------------

@router.post("/{endpoint_id}/discover-schema", response_model=SchemaDiscoveryResponse)
def discover_schema(
    endpoint_id: str,
    body: SchemaDiscoveryRequest,
    user=Depends(require_permissions("integration:write")),
) -> SchemaDiscoveryResponse:
    """Probe the endpoint (or parse its OpenAPI spec) to discover the field schema.

    The discovered schema is persisted on the endpoint record so it is
    immediately available in the field mapper.  Pass ``?path=/your-endpoint``
    to override the stored default_path for this discovery run only.
    """
    try:
        return custom_endpoint_service.discover_schema(endpoint_id, body, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ---------------------------------------------------------------------------
# Connection test
# ---------------------------------------------------------------------------

@router.post("/{endpoint_id}/test", response_model=ConnectionTestResponse)
def test_connection(
    endpoint_id: str,
    user=Depends(require_permissions("integration:read")),
) -> ConnectionTestResponse:
    """Test connectivity to the endpoint.  Returns latency and HTTP status.
    Never raises — always returns 200 with ok=false on failure.
    """
    try:
        return custom_endpoint_service.test_connection(endpoint_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Schema read (used by wizard FieldMapper)
# ---------------------------------------------------------------------------

@router.get("/{endpoint_id}/schema")
def get_schema(
    endpoint_id: str,
    user=Depends(require_permissions("integration:read")),
) -> dict:
    """Return the stored field schema for an endpoint.

    The wizard fetches this after discovery to populate the field mapper.
    Returns ``{"fields": [...], "fieldCount": N}``.
    """
    try:
        fields = custom_endpoint_service.get_field_schema(endpoint_id, tenant_id=user.tenant_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"endpointId": endpoint_id, "fields": fields, "fieldCount": len(fields)}
