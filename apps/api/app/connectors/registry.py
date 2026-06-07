"""ConnectorRegistry — singleton that all connector plugins register into."""
from __future__ import annotations

from .base import ConnectorPlugin, ConnectorTool


class ConnectorRegistry:
    """Central registry for connector plugins.

    Plugins are stateless singletons.  All per-tenant state (credentials,
    config, mode) is resolved at call-time via *tenant_id* — never stored
    inside a plugin instance.  This makes the registry safe to share across
    concurrent Celery workers and web processes without any locking.

    Usage::

        from app.connectors.registry import connector_registry
        connector_registry.register(MyPlugin())
        tools = connector_registry.get_tools("my-connector")
        result = connector_registry.execute_tool("salesforce", "create_opportunity", params, tenant_id=42)
    """

    def __init__(self) -> None:
        self._plugins: dict[str, ConnectorPlugin] = {}

    def register(self, plugin: ConnectorPlugin) -> None:
        self._plugins[plugin.connector_id] = plugin

    def list_ids(self) -> list[str]:
        return list(self._plugins.keys())

    def list_connectors(self, tenant_id: int | None = None) -> list[dict]:
        """Return summary dicts suitable for the GET /connectors response.

        *tenant_id* is used to look up per-tenant connector mode/status from
        the DB.  Falls back to the global (tenant_id IS NULL) record if no
        tenant-specific record exists.
        """
        from app.services.credential_service import credential_service
        db_modes = credential_service.all_connector_modes(tenant_id)

        result = []
        for p in self._plugins.values():
            tools = p.list_tools()
            mode   = db_modes.get(p.connector_id, "mock")
            status = "configured" if mode == "live" else "not_configured"
            result.append(
                {
                    "connectorId": p.connector_id,
                    "name": p.name,
                    "logoSlug": p.logo_slug,
                    "authScheme": p.auth_scheme,
                    "status": status,
                    "mode": mode,
                    "toolCount": len(tools),
                    "lastTestedAt": None,
                }
            )
        return result

    def get(self, connector_id: str) -> ConnectorPlugin:
        """Return the plugin for *connector_id*.

        Raises:
            KeyError: if no plugin with that ID is registered.
        """
        if connector_id not in self._plugins:
            raise KeyError(f"Unknown connector: {connector_id!r}")
        return self._plugins[connector_id]

    def get_tools(self, connector_id: str) -> list[ConnectorTool]:
        return self.get(connector_id).list_tools()

    def execute_tool(
        self,
        connector_id: str,
        tool_id: str,
        params: dict,
        tenant_id: int | None = None,
    ) -> dict:
        """Dispatch *tool_id* on *connector_id* with *params* for *tenant_id*.

        *tenant_id* is forwarded to the plugin so it can look up the correct
        tenant credentials at execution time.  Never pass tenant_id inside
        *params* — that is a legacy pattern being removed.

        Raises:
            KeyError: unknown connector or tool.
        """
        plugin = self.get(connector_id)
        return plugin.execute_tool(tool_id, params, tenant_id=tenant_id)


# Module-level singleton — imported by services and bootstrapped by __init__.py
connector_registry = ConnectorRegistry()
