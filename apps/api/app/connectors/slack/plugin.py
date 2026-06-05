"""Slack connector plugin — approved messaging tools (mock mode)."""
from __future__ import annotations

from ..base import ConnectorTool, ConnectorToolParam

_TOOLS = [
    ConnectorTool(
        "post_message",
        "Post Message",
        "Post a plain-text or markdown message to an approved Slack channel.",
        "slack",
        [
            ConnectorToolParam("channel_id", "string", True, "Approved Slack channel ID (e.g. C01234ABCDE)"),
            ConnectorToolParam("text", "string", True, "Message text (plain or mrkdwn)"),
            ConnectorToolParam("thread_ts", "string", False, "Parent message timestamp to reply in thread"),
        ],
    ),
    ConnectorTool(
        "post_block_kit",
        "Post Block Kit Message",
        "Post a structured Block Kit message to an approved channel for rich notifications.",
        "slack",
        [
            ConnectorToolParam("channel_id", "string", True, "Approved Slack channel ID"),
            ConnectorToolParam("blocks", "string", True, "JSON array of Block Kit block objects"),
            ConnectorToolParam("fallback_text", "string", False, "Accessibility fallback text"),
        ],
    ),
    ConnectorTool(
        "list_channels",
        "List Approved Channels",
        "Return the list of Slack channels the integration is approved to post into.",
        "slack",
    ),
]

_TOOL_MAP = {t.tool_id: t for t in _TOOLS}

_MOCK = {
    "post_message": {
        "ok": True,
        "channel": "C01ALERTS",
        "ts": "1748304000.000001",
        "message": {"type": "message", "text": "Mock message delivered."},
    },
    "post_block_kit": {
        "ok": True,
        "channel": "C01ALERTS",
        "ts": "1748304001.000002",
        "message": {"type": "message", "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Mock block kit message."}}]},
    },
    "list_channels": {
        "ok": True,
        "channels": [
            {"id": "C01ALERTS", "name": "alerts", "purpose": "System-generated alerts"},
            {"id": "C02REPORTS", "name": "daily-reports", "purpose": "Automated daily report summaries"},
        ],
    },
}


class SlackPlugin:
    connector_id = "slack"
    name = "Slack"
    logo_slug = "slack"
    auth_scheme = "oauth2"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown Slack tool: {tool_id!r}")
        return {"connector": "slack", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}

    def test_connection(self) -> dict:
        return {"ok": True, "message": "Slack mock connector is ready (mock mode)."}
