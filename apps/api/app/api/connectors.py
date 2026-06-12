import urllib.parse

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator, model_validator

from app.connectors import connector_registry
from fastapi import Request
from app.core.auth import get_current_user, require_permissions, require_tenant
from app.core.config import get_settings
from app.services.credential_service import credential_service
from app.models.connectors import (
    ConnectorTestResult,
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
def list_connectors(request: Request) -> list[dict]:
    """List all registered connectors. Public for SSR; includes live status when authenticated."""
    tenant_id = None
    try:
        from app.core.auth import get_current_user
        from fastapi import Header, Cookie
        authorization = request.headers.get("authorization")
        access_token = request.cookies.get("access_token")
        user = get_current_user(authorization=authorization, access_token=access_token)
        tenant_id = user.tenant_id
    except Exception:
        pass
    return connector_registry.list_connectors(tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# OAuth App Config — store Client ID + Secret from UI (no env vars needed)
# Applies to: salesforce, slack (any oauth2 connector)
# ---------------------------------------------------------------------------


class OAuthAppConfig(BaseModel):
    client_id: str
    client_secret: str
    # Optional overrides
    login_url: str = ""          # Salesforce: production vs sandbox URL
    redirect_uri: str = ""       # Override default callback URL


@router.put("/{connector_id}/oauth-app-config")
def save_oauth_app_config(
    connector_id: str,
    config: OAuthAppConfig,
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Store the OAuth2 Connected App credentials entered from the UI.

    These replace the need for SALESFORCE_CLIENT_ID / SLACK_CLIENT_ID env vars.
    Credentials are Fernet-encrypted at rest under key 'oauth_app:{connector_id}'.
    """
    allowed = {"salesforce", "slack"}
    if connector_id not in allowed:
        raise HTTPException(status_code=400, detail=f"oauth-app-config not applicable for '{connector_id}'.")
    if not config.client_id or not config.client_secret:
        raise HTTPException(status_code=422, detail="client_id and client_secret are required.")

    meta: dict = {}
    if config.login_url:
        meta["login_url_override"] = config.login_url.rstrip("/")
    if config.redirect_uri:
        meta["redirect_uri_override"] = config.redirect_uri

    credential_service.store_credentials(
        f"oauth_app:{connector_id}",
        {"client_id": config.client_id, "client_secret": config.client_secret},
        tenant_id=user.tenant_id,
        extra_meta=meta,
    )
    return {"ok": True, "message": f"{connector_id} OAuth app credentials saved. You can now click Connect."}


@router.get("/{connector_id}/oauth-app-config")
def get_oauth_app_config_status(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Return whether OAuth app credentials have been configured (never returns secrets)."""
    record = credential_service._fetch_config(f"oauth_app:{connector_id}", user.tenant_id)
    configured = record is not None and record["mode"] == "live"
    return {"connectorId": connector_id, "configured": configured}


@router.delete("/{connector_id}/oauth-app-config")
def delete_oauth_app_config(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Remove stored OAuth app credentials."""
    credential_service.revoke_token(f"oauth_app:{connector_id}", tenant_id=user.tenant_id)
    return {"ok": True, "message": f"{connector_id} OAuth app credentials removed."}


# ---------------------------------------------------------------------------
# Live-config for direct-credential connectors (NetSuite, SAP, Oracle, HCM)
# ---------------------------------------------------------------------------


class NetSuiteLiveConfig(BaseModel):
    account_id: str
    consumer_key: str
    consumer_secret: str
    token_id: str
    token_secret: str

    @field_validator("account_id", "consumer_key", "consumer_secret", "token_id", "token_secret")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field is required.")
        return v.strip()


@router.put("/netsuite/live-config")
def configure_netsuite(
    config: NetSuiteLiveConfig,
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Store encrypted NetSuite token-based OAuth credentials entered from the UI."""
    from app.services.schema_cache import schema_cache
    credential_service.store_credentials(
        "netsuite",
        {
            "account_id":       config.account_id,
            "consumer_key":     config.consumer_key,
            "consumer_secret":  config.consumer_secret,
            "token_id":         config.token_id,
            "token_secret":     config.token_secret,
        },
        tenant_id=user.tenant_id,
        extra_meta={"account_id_display": config.account_id},
    )
    schema_cache.invalidate("netsuite", tenant_id=user.tenant_id)
    return {"ok": True, "message": f"NetSuite credentials saved for account {config.account_id}."}


@router.delete("/netsuite/live-config/disconnect")
def disconnect_netsuite(
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("netsuite", tenant_id=user.tenant_id)
    schema_cache.invalidate("netsuite", tenant_id=user.tenant_id)
    return {"ok": True, "message": "NetSuite connector disconnected."}


class SAPLiveConfig(BaseModel):
    """Two connection modes, mirroring the live connector's auth modes:

    - **Production** (Basic Auth): host + client + username + password.
      How real S/4HANA Cloud / on-prem Gateway systems authenticate.
    - **Sandbox** (APIKey header): host + api_key (+ optional api_base_path).
      For the free, public SAP Business Accelerator Hub Sandbox
      (sandbox.api.sap.com) — obtained via self-service signup at
      api.sap.com, no real SAP system required. When api_key is supplied,
      username/password/client are not required.
    """

    host: str
    client: str = "100"
    username: str = ""
    password: str = ""
    system_number: str = "00"
    api_key: str = ""
    api_base_path: str = ""

    @field_validator("host")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field is required.")
        return v.strip()

    @model_validator(mode="after")
    def require_one_auth_mode(self) -> "SAPLiveConfig":
        has_basic = bool(self.username.strip() and self.password.strip())
        has_api_key = bool(self.api_key.strip())
        if not has_basic and not has_api_key:
            raise ValueError(
                "Provide either username + password (production system) "
                "or an API key (SAP Business Accelerator Hub Sandbox)."
            )
        return self


@router.put("/sap/live-config")
def configure_sap(
    config: SAPLiveConfig,
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Store encrypted SAP credentials entered from the UI."""
    from app.services.schema_cache import schema_cache
    sandbox_mode = bool(config.api_key.strip())
    credential_service.store_credentials(
        "sap",
        {
            "host":          config.host,
            "client":        config.client,
            "username":      config.username,
            "password":      config.password,
            "system_number": config.system_number,
            "api_key":       config.api_key,
            "api_base_path": config.api_base_path,
        },
        tenant_id=user.tenant_id,
        extra_meta={
            "host_display": config.host,
            "client_display": "sandbox (APIKey)" if sandbox_mode else config.client,
        },
    )
    schema_cache.invalidate("sap", tenant_id=user.tenant_id)
    mode_msg = "API key (sandbox mode)" if sandbox_mode else f"client {config.client}"
    return {"ok": True, "message": f"SAP credentials saved for host {config.host} ({mode_msg})."}


@router.delete("/sap/live-config/disconnect")
def disconnect_sap(
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("sap", tenant_id=user.tenant_id)
    schema_cache.invalidate("sap", tenant_id=user.tenant_id)
    return {"ok": True, "message": "SAP connector disconnected."}


class OracleLiveConfig(BaseModel):
    host: str
    port: str = "1521"
    service_name: str
    username: str
    password: str

    @field_validator("host", "service_name", "username", "password")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field is required.")
        return v.strip()


@router.put("/oracle/live-config")
def configure_oracle(
    config: OracleLiveConfig,
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Store encrypted Oracle DB credentials entered from the UI."""
    from app.services.schema_cache import schema_cache
    credential_service.store_credentials(
        "oracle",
        {
            "host":         config.host,
            "port":         config.port,
            "service_name": config.service_name,
            "username":     config.username,
            "password":     config.password,
        },
        tenant_id=user.tenant_id,
        extra_meta={"host_display": config.host, "service_name_display": config.service_name},
    )
    schema_cache.invalidate("oracle", tenant_id=user.tenant_id)
    return {"ok": True, "message": f"Oracle credentials saved for {config.host}/{config.service_name}."}


@router.delete("/oracle/live-config/disconnect")
def disconnect_oracle(
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("oracle", tenant_id=user.tenant_id)
    schema_cache.invalidate("oracle", tenant_id=user.tenant_id)
    return {"ok": True, "message": "Oracle connector disconnected."}


class HCMLiveConfig(BaseModel):
    tenant_url: str
    client_id: str
    client_secret: str
    # Some HCM deployments use basic auth instead of OAuth client credentials
    username: str = ""
    password: str = ""

    @field_validator("tenant_url", "client_id", "client_secret")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field is required.")
        return v.strip()

    @field_validator("tenant_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("tenant_url must start with https://")
        return v


@router.put("/hcm/live-config")
def configure_hcm(
    config: HCMLiveConfig,
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Store encrypted HCM (Workday) credentials entered from the UI."""
    from app.services.schema_cache import schema_cache
    credential_service.store_credentials(
        "hcm",
        {
            "tenant_url":    config.tenant_url,
            "client_id":     config.client_id,
            "client_secret": config.client_secret,
            "username":      config.username,
            "password":      config.password,
        },
        tenant_id=user.tenant_id,
        extra_meta={"tenant_url_display": config.tenant_url},
    )
    schema_cache.invalidate("hcm", tenant_id=user.tenant_id)
    return {"ok": True, "message": f"HCM credentials saved for tenant {config.tenant_url}."}


@router.delete("/hcm/live-config/disconnect")
def disconnect_hcm(
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("hcm", tenant_id=user.tenant_id)
    schema_cache.invalidate("hcm", tenant_id=user.tenant_id)
    return {"ok": True, "message": "HCM connector disconnected."}


# ---------------------------------------------------------------------------
# Slack OAuth2 routes — must appear BEFORE /{connector_id} catch-all
# ---------------------------------------------------------------------------


def _get_oauth_app_creds(connector_id: str, tenant_id: int | None) -> dict | None:
    """Return decrypted OAuth app credentials stored via the UI, or None if not set."""
    return credential_service.get_credentials(f"oauth_app:{connector_id}", tenant_id=tenant_id)


@router.get("/slack/oauth/authorize")
def slack_oauth_authorize(user=Depends(require_permissions("connector:admin"))) -> RedirectResponse:
    """Redirect the user to Slack's OAuth2 authorisation page.

    Client ID / Secret are pulled from credentials stored via the UI first;
    falls back to SLACK_CLIENT_ID env var for backwards compatibility.
    """
    settings = get_settings()
    # DB-first: credentials saved through the UI
    db_creds = _get_oauth_app_creds("slack", tenant_id=user.tenant_id)
    client_id = (db_creds or {}).get("client_id") or settings.slack_client_id
    redirect_uri = settings.slack_redirect_uri

    if not client_id:
        raise HTTPException(
            status_code=501,
            detail="Slack OAuth is not configured. Enter your Slack App Client ID and Secret in the Connector Registry.",
        )
    params = {
        "client_id": client_id,
        "scope": settings.slack_scopes,
        "redirect_uri": redirect_uri,
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

    # DB-first credential resolution
    db_creds = _get_oauth_app_creds("slack", tenant_id=None)
    client_id     = (db_creds or {}).get("client_id")     or settings.slack_client_id
    client_secret = (db_creds or {}).get("client_secret") or settings.slack_client_secret

    # Exchange code for access token
    try:
        resp = httpx.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id":     client_id,
                "client_secret": client_secret,
                "code":          code,
                "redirect_uri":  settings.slack_redirect_uri,
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
def slack_oauth_disconnect(
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Revoke the stored Slack token and reset to mock mode."""
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("slack", tenant_id=user.tenant_id)
    schema_cache.invalidate("slack", tenant_id=user.tenant_id)
    return {"ok": True, "message": "Slack connector disconnected and reset to mock mode."}


# ---------------------------------------------------------------------------
# Salesforce OAuth2 routes — must appear BEFORE /{connector_id} catch-all
# ---------------------------------------------------------------------------


@router.get("/salesforce/oauth/authorize")
def salesforce_oauth_authorize(user=Depends(require_permissions("connector:admin"))) -> RedirectResponse:
    """Redirect the user to Salesforce's OAuth2 authorisation page.

    Client ID / Secret + optional login URL are pulled from credentials stored
    via the UI first; falls back to SALESFORCE_CLIENT_ID env var.

    The tenant_id is encoded in the OAuth `state` parameter so the callback
    (which has no authenticated user) can look up the right credentials and
    store the resulting token under the correct tenant.
    """
    settings = get_settings()
    db_creds  = _get_oauth_app_creds("salesforce", tenant_id=user.tenant_id)
    client_id = (db_creds or {}).get("client_id") or settings.salesforce_client_id

    # Resolve login URL: check stored override first, then env var default
    raw_record = credential_service._fetch_config("oauth_app:salesforce", user.tenant_id)
    login_url = ((raw_record or {}).get("config") or {}).get("login_url_override") or settings.salesforce_login_url

    if not client_id:
        raise HTTPException(
            status_code=501,
            detail="Salesforce OAuth is not configured. Enter your Connected App Client ID and Secret in the Connector Registry.",
        )
    params = {
        "response_type": "code",
        "client_id":     client_id,
        "redirect_uri":  settings.salesforce_redirect_uri,
        "scope":         "api refresh_token offline_access",
        # Encode tenant_id in state so the callback can look up credentials
        # and store the token under the correct tenant without needing a JWT.
        "state":         str(user.tenant_id) if user.tenant_id is not None else "",
    }
    url = f"{login_url}/services/oauth2/authorize?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@router.get("/salesforce/oauth/callback")
def salesforce_oauth_callback(
    code: str = "",
    error: str = "",
    error_description: str = "",
    state: str = "",
) -> RedirectResponse:
    """Salesforce OAuth2 callback — exchange code for token, store encrypted, redirect to UI.

    The `state` parameter carries the tenant_id from the authorize redirect so
    we can look up the right Connected App credentials and store the resulting
    token under the correct tenant — without needing an authenticated user in
    this browser-redirect request.
    """
    settings = get_settings()
    frontend_base = settings.app_base_url

    if error:
        msg = error_description or error
        return RedirectResponse(
            f"{frontend_base}/connectors?salesforce_error={urllib.parse.quote(msg)}"
        )

    if not code:
        return RedirectResponse(f"{frontend_base}/connectors?salesforce_error=missing_code")

    # Recover tenant_id from the OAuth state parameter (set in /authorize).
    tenant_id: int | None = int(state) if state and state.isdigit() else None

    # DB-first credential resolution using the tenant that initiated the flow.
    db_creds      = _get_oauth_app_creds("salesforce", tenant_id=tenant_id)
    client_id     = (db_creds or {}).get("client_id")     or settings.salesforce_client_id
    client_secret = (db_creds or {}).get("client_secret") or settings.salesforce_client_secret
    # Resolve login URL — check stored override, fall back to settings
    raw_record = credential_service._fetch_config("oauth_app:salesforce", tenant_id)
    login_url  = ((raw_record or {}).get("config") or {}).get("login_url_override") or settings.salesforce_login_url

    try:
        resp = httpx.post(
            f"{login_url}/services/oauth2/token",
            data={
                "grant_type":    "authorization_code",
                "client_id":     client_id,
                "client_secret": client_secret,
                "redirect_uri":  settings.salesforce_redirect_uri,
                "code":          code,
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

    # Store encrypted OAuth token under the tenant that initiated the flow.
    credential_service.store_oauth_token("salesforce", token_data, tenant_id=tenant_id)

    # Bust the schema cache so the next Fields/schema request fetches live data.
    try:
        from app.services.schema_cache import schema_cache
        schema_cache.invalidate("salesforce", tenant_id=tenant_id)
    except Exception:
        pass  # Cache invalidation is best-effort — don't fail the OAuth flow

    instance_url = token_data.get("instance_url", "your Salesforce org")
    return RedirectResponse(
        f"{frontend_base}/connectors?salesforce_connected=1&instance_url={urllib.parse.quote(instance_url)}"
    )


@router.delete("/salesforce/oauth/disconnect")
def salesforce_oauth_disconnect(
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Revoke the stored Salesforce token and reset to mock mode."""
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("salesforce", tenant_id=user.tenant_id)
    schema_cache.invalidate("salesforce", tenant_id=user.tenant_id)
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
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("rest-api", tenant_id=user.tenant_id)
    schema_cache.invalidate("rest-api", tenant_id=user.tenant_id)
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
    from app.services.schema_cache import schema_cache
    credential_service.revoke_token("postgres", tenant_id=user.tenant_id)
    schema_cache.invalidate("postgres", tenant_id=user.tenant_id)
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


@router.post("/{connector_id}/test", response_model=ConnectorTestResult)
def test_connector(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> ConnectorTestResult:
    """Test the connection for any registered connector.

    Returns a normalised ConnectorTestResult (ok, mode, message) regardless
    of which plugin handles the request.  Unknown keys from the plugin response
    are stripped; missing keys receive safe defaults.
    """
    try:
        plugin = connector_registry.get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    # Pass tenant_id to plugins that support it (oauth2 connectors like Salesforce/Slack)
    import inspect as _inspect
    if "tenant_id" in _inspect.signature(plugin.test_connection).parameters:
        raw = plugin.test_connection(tenant_id=user.tenant_id)
    else:
        raw = plugin.test_connection()
    return ConnectorTestResult(
        ok=raw.get("ok", False),
        mode=raw.get("mode", "mock"),
        message=raw.get("message", "No message returned by connector."),
    )


@router.get("/{connector_id}/schema", response_model=dict)
def get_connector_schema(
    connector_id: str,
    refresh: bool = False,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Return the schema (objects + fields) exposed by this connector.

    Schemas are cached per (connector_id, tenant_id):
    - Mock connectors: indefinitely (schema never changes).
    - Live connectors: 5 minutes (SCHEMA_CACHE_TTL_SECONDS env var overrides).

    Pass ?refresh=true to bypass the cache and force a fresh fetch.
    Schema is used to populate the Data Mapping Studio source/target trays.
    """
    from datetime import UTC, datetime
    from app.models.connectors import ConnectorSchema, ConnectorSchemaField, ConnectorSchemaObject
    from app.services.schema_cache import schema_cache

    try:
        plugin = connector_registry.get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    tenant_id = user.tenant_id

    # ── Cache lookup ──────────────────────────────────────────────────────────
    if not refresh:
        cached = schema_cache.get(connector_id, tenant_id)
        if cached is not None:
            return cached

    # ── Fresh fetch ───────────────────────────────────────────────────────────
    try:
        raw_objects = plugin.fetch_schema(tenant_id=tenant_id)
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "Schema fetch failed for connector %r (tenant %s): %s",
            connector_id,
            tenant_id,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="Schema fetch failed. Check connector credentials and try again.",
        )

    # Pass tenant_id to plugins that support it so live mode is detected correctly
    import inspect as _inspect
    if "tenant_id" in _inspect.signature(plugin.test_connection).parameters:
        test_result = plugin.test_connection(tenant_id=tenant_id)
    else:
        test_result = plugin.test_connection()
    mode = test_result.get("mode", "mock")
    is_mock = (mode == "mock")

    schema_objects = [
        ConnectorSchemaObject(
            objectId=obj.object_id,
            label=obj.label,
            fields=[
                ConnectorSchemaField(
                    name=f.name,
                    label=f.label,
                    type=f.type,
                    required=f.required,
                    updateable=f.updateable,
                    sample=f.sample,
                )
                for f in obj.fields
            ],
        )
        for obj in raw_objects
    ]

    schema = ConnectorSchema(
        connectorId=connector_id,
        mode=mode,
        objects=schema_objects,
        fetchedAt=datetime.now(UTC).isoformat(),
    )
    result = schema.model_dump()

    # ── Cache store ───────────────────────────────────────────────────────────
    schema_cache.set(connector_id, result, tenant_id=tenant_id, is_mock=is_mock)

    return result


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


# ---------------------------------------------------------------------------
# Generic per-tenant connector config — must come AFTER all specific-path
# legacy routes so FastAPI's route matching doesn't shadow them.
# ---------------------------------------------------------------------------


@router.get("/{connector_id}/config", response_model=dict)
def get_connector_config(
    connector_id: str,
    user=Depends(require_permissions("connector:admin")),
) -> dict:
    """Return non-secret configuration metadata for a connector scoped to the calling tenant.

    Credentials (API keys, tokens) are never returned — only metadata such as
    base URLs, account IDs, and mode flags.  This is a tenant-scoped view:
    tenant A's Salesforce config is completely isolated from tenant B's.
    """
    try:
        connector_registry.get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    record = credential_service._fetch_config(connector_id, user.tenant_id)  # noqa: SLF001
    if record is None:
        return {
            "connectorId": connector_id,
            "tenantId": user.tenant_id,
            "mode": "mock",
            "status": "not_configured",
            "meta": {},
        }
    config = record.get("config", {})
    _SECRETS = {"api_key", "access_token", "refresh_token", "connection_string", "token_secret", "consumer_secret", "password"}
    safe_meta = {k: v for k, v in config.items() if k not in _SECRETS}
    return {
        "connectorId": connector_id,
        "tenantId": user.tenant_id,
        "mode": record.get("mode", "mock"),
        "status": record.get("status", "not_configured"),
        "meta": safe_meta,
    }


@router.put("/{connector_id}/config", response_model=dict)
def update_connector_config(
    connector_id: str,
    body: dict = Body(...),
    user=Depends(require_permissions("connector:admin")),
    _tenant=Depends(require_tenant),
) -> dict:
    """Update non-secret configuration metadata for a connector (per-tenant).

    Stores only metadata (account IDs, base URLs, feature flags).
    Secrets (API keys, tokens, passwords) must go through the dedicated
    auth endpoints — submitting them here returns 422.
    """
    try:
        connector_registry.get(connector_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    _SECRETS = {"api_key", "access_token", "refresh_token", "connection_string", "password", "token_secret", "consumer_secret"}
    if leaked := set(body.keys()) & _SECRETS:
        raise HTTPException(
            status_code=422,
            detail=f"Secrets must not be stored via this endpoint. Use the dedicated auth route for: {sorted(leaked)}",
        )

    mode = body.pop("mode", "mock")
    credential_service._upsert_config(connector_id, user.tenant_id, body, status="configured", mode=mode)  # noqa: SLF001
    return {"ok": True, "connectorId": connector_id, "tenantId": user.tenant_id, "message": "Config updated."}
