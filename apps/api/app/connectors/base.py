"""Base protocol and data classes for connector plugins."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ConnectorToolParam:
    name: str
    type: str  # "string" | "number" | "boolean"
    required: bool
    description: str


@dataclass(frozen=True)
class ConnectorTool:
    tool_id: str
    label: str
    description: str
    connector_id: str
    params: list[ConnectorToolParam] = field(default_factory=list)


@runtime_checkable
class ConnectorPlugin(Protocol):
    """Interface that every connector plugin must satisfy."""

    connector_id: str
    name: str
    logo_slug: str
    auth_scheme: str  # "none" | "api_key" | "oauth2" | "basic" | "token_based"

    def list_tools(self) -> list[ConnectorTool]:
        """Return all tools available on this connector."""
        ...

    def execute_tool(self, tool_id: str, params: dict) -> dict:
        """Execute a tool and return a result dict.

        Raises:
            KeyError: if tool_id is not registered for this connector.
        """
        ...

    def test_connection(self) -> dict:
        """Test connectivity.  Returns ``{"ok": bool, "message": str}``."""
        ...
