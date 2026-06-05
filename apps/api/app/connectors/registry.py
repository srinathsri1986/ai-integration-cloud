"""ConnectorRegistry — singleton that all connector plugins register into."""
from __future__ import annotations

from .base import ConnectorPlugin, ConnectorTool


class ConnectorRegistry:
    """Central registry for connector plugins.

    Usage::

        from app.connectors.registry import connector_registry
        connector_registry.register(MyPlugin())
        tools = connector_registry.get_tools("my-connector")
    """

    def __init__(self) -> None:
        self._plugins: dict[str, ConnectorPlugin] = {}

    def register(self, plugin: ConnectorPlugin) -> None:
        self._plugins[plugin.connector_id] = plugin

    def list_ids(self) -> list[str]:
        return list(self._plugins.keys())

    def list_connectors(self) -> list[dict]:
        """Return summary dicts suitable for the GET /connectors response."""
        result = []
        for p in self._plugins.values():
            tools = p.list_tools()
            result.append(
                {
                    "connectorId": p.connector_id,
                    "name": p.name,
                    "logoSlug": p.logo_slug,
                    "authScheme": p.auth_scheme,
                    "status": "configured",
                    "mode": "mock",
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

    def execute_tool(self, connector_id: str, tool_id: str, params: dict) -> dict:
        """Dispatch *tool_id* on *connector_id* with *params*.

        Raises:
            KeyError: unknown connector or tool.
        """
        plugin = self.get(connector_id)
        return plugin.execute_tool(tool_id, params)


# Module-level singleton — imported by services and bootstrapped by __init__.py
connector_registry = ConnectorRegistry()
