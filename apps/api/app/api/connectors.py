import urllib.parse

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator

from app.connectors import connector_registry
from app.core.auth import require_permissions
from app.core.config import get_settings
from app.services.credential_service import credential_service
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
    """List all registered connectors with live status from DB where available."""
    items = connector_registry.list_connectors()
    db_modes = credential_service.all_connector_modes()
    for item in items:
        cid = item["connectorId"]
        if cid in db_modes:
            item["mode"] = db_modes[cid]
            item["status"] = "configured" if db_modes[cid] == "live" else "not_configured"
    return items


# ---------------------------------------------------------------------------
# Slack OAuth2 routes — must appear BEFORE /{connector_id} catch-all
# ---------------------------------------------------------------------------


@router.get("/slack/oauth/authorize")
def slack_oauth_authorize() -> RedirectResponse:
    """Redirect the user to Slack's OAuth2 authorisation page.

    Register your Slack app redirect URI as:
        http://localhost:8000/api/v1/connectors/slack/oauth/callback
    """
    settings = get_settings()
    if not settings.slack_client_id:
        raise HTTPException(
            status_code=501,
            detail="Slack OAuth is not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET.",
        )
    params = {
        "client_id": settings.slack_client_id,
        "scope": settings.slack_scopes,
        "redirect_uri": settings.slack_redirect_uri,
    }
    url = "https://slack.com/oauth/v2/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/slack/oauth/callback")
def slack_oauth_callback(code: str = "", error: str = "") -> RedirectResponse:
    """Slack OAuth2 callback — exchange code for token, store encrypted, redirect to UI."""
    settings = get_settings()
    frontend_base = settings.app_base_url

    if error:
        return RedirectResponse(f"{frontend_base}/connectors?slack_error={urllib.parse.quote(error)}")

    if not code:
        return RedirectResponse(f"{frontend_base}/connectors?slack_error=missing_code")

    # Exchange code for access token
    try:
        resp = httpx.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": settings.slack_client_id,
                "client_secret": settings.slack_client_secret,
                "code": code,
                "redirect_uri": settings.slack_redirect_uri,
            },
            timeout=10,
        )
        token_data = resp.json()
    except Exception as exc:
        return RedirectResponse(
            f"{frontend_base}/connectors?slack_error={urllib.parse.quote(str(exc))}"
        )

    if not token_data.get("ok"):
        error_msg = token_data.get("error", "unknown_error")
        return RedirectResponse(
            f"{frontend_base}/connectors?slack_error={urllib.parse.quote(error_msg)}"
        )

    # Store encrypted token
    credential_service.store_oauth_token("slack", token_data, tenant_id=None)

    workspace = (
        token_data.get("team", {}).get("name", "your workspace")
        if isinstance(token_data.get("team"), dict)
        else "your workspace"
    )
    return RedirectResponse(
        f"{frontend_base}/connectors?slack_connected=1&workspace={urllib.parse.quote(workspace)}"
    )


@router.delete("/slack/oauth/disconnect")
def slack_oauth_disconnect(user=Depends(require_permissions("connector:admin"))) -> dict:
    """Revoke the stored Slack token and reset to mock mode."""
    credential_service.revoke_token("slack", tenant_id=None)
    return {"ok": True, "message": "Slack connector disconnected and reset to mock mode."}


# ---------------------------------------------------------------------------
# Salesforce OAuth2 routes — must appear BEFORE /{connector_id} catch-all
# ---------------------------------------------------------------------------


@router.get("/salesforce/oauth/authorize")
def salesforce_oauth_authorize() -> RedirectResponse:
    """Redirect the user to Salesforce's OAuth2 authorisation page.

    Create a Connected App in Salesforce Setup → App Manager and set the
    callback URL to:
        http://localhost:8000/api/v1/connectors/salesforce/oauth/callback
    """
    settings = get_settings()
    if not settings.salesforce_client_id:
        raise HTTPException(
            status_code=501,
            detail="Salesforce OAuth is not configured. Set SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET.",
        )
    params = {
        "response_type": "code",
        "client_id": settings.salesforce_client_id,
        "redirect_uri": settings.salesforce_redirect_uri,
        "scope": "api refresh_token",
    }
    url = f"{settings.salesforce_login_url}/services/oauth2/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/salesforce/oauth/callback")
def salesforce_oauth_callback(code: str = "", error: str = "", error_description: str = "") -> RedirectResponse:
    """Salesforce OAuth2 callback — exchange code for token, store encrypted, redirect to UI."""
    settings = get_settings()
    frontend_base = settings.app_base_url

    if error:
        msg = error_description or error
        return RedirectResponse(
            f"{frontend_base}/connectors?salesforce_error={urllib.parse.quote(msg)}"
        )

    if not code:
        return RedirectResponse(f"{frontend_base}/connectors?salesforce_error=missing_code")

    try:
        resp = httpx.post(
            f"{settings.salesforce_login_url}/services/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.salesforce_client_id,
                "client_secret": settings.salesforce_client_secret,
                "redirect_uri": settings.salesforce_redirect_uri,
                "code": code,
            },
            timeout=15,
        )
        token_data = resp.json()
    except Exception as exc:
        return RedirectResponse(
            f"{frontend_base}/connectors?salesforce_error={urllib.parse.quote(str(exc))}"
        )

    if "error" in token_data:
        return RedirectResponse(
            f"{frontend_base}/connectors?salesforce_error={urllib.parse.quote(token_data.get('error_description', token_data['error']))}"
        )

    # Store encrypted OAuth token (includes access_token, refresh_token, instance_url)
    credential_service.store_oauth_token("salesforce", token_data, tenant_id=None)

    instance_url = token_data.get("instance_url", "your Salesforce org")
    return RedirectResponse(
        f"{frontend_base}/connectors?salesforce_connected=1&instance_url={urllib.parse.quote(instance_url)}"
    )


@router.delete("/salesforce/oauth/disconnect")
def salesforce_oauth_disconnect(user=Depends(require_permissions("connector:admin"))) -> dict:
    """Revoke the stored Salesforce token and reset to mock mode."""
    credential_service.revoke_token("salesforce", tenant_id=None)
    return {"ok": True, "message": "Salesforce connector disconnected and reset to mock mode."}


# ---------------------------------------------------------------------------
# REST API connector — API key + base URL configuration
# ---------------------------------------------------------------------------


class RestApiLiveConfig(BaseModel):
    base_url: str
    api_key: str

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v


@router.put("/rest-api/live-config")
def configure_rest_api(
    config: RestApiLiveConfig,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Store encrypted API key + base URL for the REST API connector."""
    credential_service.store_credentials(
        "rest-api",
        {"base_url": config.base_url, "api_key": config.api_key},
        tenant_id=None,
        extra_meta={"base_url_display": config.base_url},
    )
    return {"ok": True, "message": f"REST API connector configured for {config.base_url}."}


@router.delete("/rest-api/live-config/disconnect")
def disconnect_rest_api(user=Depends(require_permissions("connector:admin"))) -> dict:
    """Remove REST API credentials and reset to mock mode."""
    credential_service.revoke_token("rest-api", tenant_id=None)
    return {"ok": True, "message": "REST API connector disconnected and reset to mock mode."}


# ---------------------------------------------------------------------------
# PostgreSQL connector — connection string configuration
# ---------------------------------------------------------------------------


class PostgresLiveConfig(BaseModel):
    connection_string: str

    @field_validator("connection_string")
    @classmethod
    def validate_conn_str(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("postgres://") or v.startswith("postgresql://")):
            raise ValueError("connection_string must start with postgres:// or postgresql://")
        return v


@router.put("/postgres/live-config")
def configure_postgres(
    config: PostgresLiveConfig,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Store encrypted connection string for the PostgreSQL connector."""
    # Extract host for display (don't store password in plaintext meta)
    host = config.connection_string.split("@")[-1].split("/")[0] if "@" in config.connection_string else "configured"
    credential_service.store_credentials(
        "postgres",
        {"connection_string": config.connection_string},
        tenant_id=None,
        extra_meta={"host_display": host},
    )
    return {"ok": True, "message": f"PostgreSQL connector configured for host {host}."}


@router.delete("/postgres/live-config/disconnect")
def disconnect_postgres(user=Depends(require_permissions("connector:admin"))) -> dict:
    """Remove PostgreSQL credentials and reset to mock mode."""
    credential_service.revoke_token("postgres", tenant_id=None)
    return {"ok": True, "message": "PostgreSQL connector disconnected and reset to mock mode."}


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
