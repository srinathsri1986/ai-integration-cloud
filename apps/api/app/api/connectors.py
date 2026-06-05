from fastapi import APIRouter, Depends, HTTPException

from app.connectors import connector_registry
from app.core.auth import require_permissions
from app.models.connectors import (
    ConnectorListItem,
    NetSuiteConnectionTestResponse,
    NetSuiteConnectorConfig,
    NetSuiteConnectorConfigUpdate,
    RestApiApprovedObject,
    RestApiConnectionTestResponse,
    RestApiConnectorConfig,
    RestApiConnectorConfigUpdate,
    RestApiSchemaDiscoveryRequest,
    RestApiSchemaDiscoveryResponse,
    RestApiSchemaPromotionRequest,
    RestApiSchemaPromotionResponse,
)
from app.services.connector_config_service import connector_config_service

router = APIRouter(prefix="/connectors", tags=["connectors"])


# ---------------------------------------------------------------------------
# Generic connector routes (connector-agnostic, backed by ConnectorRegistry)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[dict])
def list_connectors(user=Depends(require_permissions("connector:admin"))) -> list[dict]:
    """List all registered connectors with status, mode, and tool count."""
    return connector_registry.list_connectors()


@router.get("/{connector_id}/tools", response_model=list[dict])
def list_connector_tools(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> list[dict]:
    """List the approved tools for a connector."""
    try:
        tools = connector_registry.get_tools(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return [
        {
            "toolId": t.tool_id,
            "label": t.label,
            "description": t.description,
            "connectorId": t.connector_id,
            "params": {
                p.name: {"type": p.type, "required": p.required, "description": p.description}
                for p in (t.params or [])
            },
        }
        for t in tools
    ]


@router.post("/{connector_id}/test", response_model=dict)
def test_connector(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Test the connection for any registered connector."""
    try:
        plugin = connector_registry.get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return plugin.test_connection()


@router.get("/{connector_id}", response_model=dict)
def get_connector(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Get a single connector definition with its full tool catalogue."""
    try:
        plugin = connector_registry.get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    tools = plugin.list_tools()
    return {
        "connectorId": plugin.connector_id,
        "name": plugin.name,
        "logoSlug": plugin.logo_slug,
        "authScheme": plugin.auth_scheme,
        "status": "configured",
        "mode": "mock",
        "toolCount": len(tools),
        "lastTestedAt": None,
        "tools": [
            {
                "toolId": t.tool_id,
                "label": t.label,
                "description": t.description,
                "connectorId": t.connector_id,
                "params": {
                    p.name: {"type": p.type, "required": p.required, "description": p.description}
                    for p in (t.params or [])
                },
            }
            for t in tools
        ],
    }


# ---------------------------------------------------------------------------
# Legacy NetSuite-specific routes (kept for backward compatibility)
# ---------------------------------------------------------------------------


@router.get("/netsuite/config", response_model=NetSuiteConnectorConfig)
def get_netsuite_config(user=Depends(require_permissions("connector:admin"))) -> NetSuiteConnectorConfig:
    return connector_config_service.get_netsuite_config()


@router.post("/netsuite/legacy-test", response_model=NetSuiteConnectionTestResponse)
def test_netsuite_connection_legacy(user=Depends(require_permissions("connector:admin"))) -> NetSuiteConnectionTestResponse:
    return connector_config_service.test_netsuite_connection()


@router.put("/netsuite/config", response_model=NetSuiteConnectorConfig)
def update_netsuite_config(
    update: NetSuiteConnectorConfigUpdate,
    user=Depends(require_permissions("connector:admin")),
) -> NetSuiteConnectorConfig:
    return connector_config_service.update_netsuite_config(update)


# ---------------------------------------------------------------------------
# Legacy REST API-specific routes (kept for backward compatibility)
# ---------------------------------------------------------------------------


@router.get("/rest-api/config", response_model=RestApiConnectorConfig)
def get_rest_api_config(user=Depends(require_permissions("connector:admin"))) -> RestApiConnectorConfig:
    return connector_config_service.get_rest_api_config()


@router.get("/rest-api/objects", response_model=list[RestApiApprovedObject])
def list_rest_api_objects(user=Depends(require_permissions("connector:admin"))) -> list[RestApiApprovedObject]:
    return connector_config_service.approved_rest_api_objects()


@router.post("/rest-api/discover-schema", response_model=RestApiSchemaDiscoveryResponse)
def discover_rest_api_schema(
    request: RestApiSchemaDiscoveryRequest,
    user=Depends(require_permissions("connector:admin")),
) -> RestApiSchemaDiscoveryResponse:
    return connector_config_service.discover_rest_api_schema(request)


@router.post("/rest-api/promote-schema", response_model=RestApiSchemaPromotionResponse)
def promote_rest_api_schema(
    request: RestApiSchemaPromotionRequest,
    user=Depends(require_permissions("connector:admin")),
) -> RestApiSchemaPromotionResponse:
    return connector_config_service.promote_rest_api_schema(request)


@router.post("/rest-api/legacy-test", response_model=RestApiConnectionTestResponse)
def test_rest_api_connection_legacy(user=Depends(require_permissions("connector:admin"))) -> RestApiConnectionTestResponse:
    return connector_config_service.test_rest_api_connection()


@router.put("/rest-api/config", response_model=RestApiConnectorConfig)
def update_rest_api_config(
    update: RestApiConnectorConfigUpdate,
    user=Depends(require_permissions("connector:admin")),
) -> RestApiConnectorConfig:
    return connector_config_service.update_rest_api_config(update)
