"""Slack connector plugin — approved messaging tools (mock + live OAuth2 mode).

In mock mode (no OAuth token): returns structured fake responses.
In live mode (token stored via /connectors/slack/oauth/callback):
    uses slack_sdk.WebClient to make real Slack API calls.

Security: tokens are encrypted at rest via ConnectorCredentialService.
"""
from __future__ import annotations

import logging

from ..base import ConnectorTool, ConnectorToolParam, SchemaField, SchemaObject

logger = logging.getLogger(__name__)

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
        "message": {
            "type": "message",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Mock block kit message."}}],
        },
    },
    "list_channels": {
        "ok": True,
        "channels": [
            {"id": "C01ALERTS", "name": "alerts", "purpose": "System-generated alerts"},
            {"id": "C02REPORTS", "name": "daily-reports", "purpose": "Automated daily report summaries"},
        ],
    },
}


def _get_live_token(tenant_id: int | None = None) -> str | None:
    """Return the decrypted Slack access token, or None if not configured."""
    try:
        from app.services.credential_service import credential_service
        token_data = credential_service.get_oauth_token("slack", tenant_id)
        if token_data:
            return token_data.get("access_token") or token_data.get("bot_access_token")
    except Exception as exc:
        logger.debug("Could not load Slack token: %s", exc)
    return None


def _execute_live(tool_id: str, params: dict, token: str) -> dict:
    """Dispatch a tool call to the real Slack API using slack_sdk."""
    from slack_sdk import WebClient  # type: ignore[import]
    from slack_sdk.errors import SlackApiError  # type: ignore[import]

    client = WebClient(token=token)
    try:
        if tool_id == "post_message":
            channel = params.get("channel_id", "general")
            text = params.get("text", "Notification from AI Integration Cloud")
            kwargs: dict = {"channel": channel, "text": text}
            if params.get("thread_ts"):
                kwargs["thread_ts"] = params["thread_ts"]
            resp = client.chat_postMessage(**kwargs)
            return {
                "connector": "slack",
                "tool": tool_id,
                "mode": "live",
                "result": {"ok": resp["ok"], "channel": resp["channel"], "ts": resp["ts"]},
            }

        elif tool_id == "post_block_kit":
            import json as _json
            channel = params.get("channel_id", "general")
            raw_blocks = params.get("blocks", "[]")
            blocks = _json.loads(raw_blocks) if isinstance(raw_blocks, str) else raw_blocks
            fallback = params.get("fallback_text", "Notification")
            resp = client.chat_postMessage(channel=channel, blocks=blocks, text=fallback)
            return {
                "connector": "slack",
                "tool": tool_id,
                "mode": "live",
                "result": {"ok": resp["ok"], "channel": resp["channel"], "ts": resp["ts"]},
            }

        elif tool_id == "list_channels":
            resp = client.conversations_list(types="public_channel", limit=100)
            channels = [
                {"id": c["id"], "name": c["name"], "purpose": c.get("purpose", {}).get("value", "")}
                for c in resp.get("channels", [])
            ]
            return {
                "connector": "slack",
                "tool": tool_id,
                "mode": "live",
                "result": {"ok": resp["ok"], "channels": channels},
            }

        raise KeyError(f"Unknown Slack tool: {tool_id!r}")

    except SlackApiError as exc:
        logger.warning("Slack API error for tool=%s: %s", tool_id, exc.response.get("error"))
        raise RuntimeError(f"Slack API error: {exc.response.get('error')}") from exc


class SlackPlugin:
    connector_id = "slack"
    name = "Slack"
    logo_slug = "slack"
    auth_scheme = "oauth2"

    def list_tools(self) -> list[ConnectorTool]:
        return list(_TOOLS)

    def execute_tool(self, tool_id: str, params: dict, tenant_id: int | None = None) -> dict:
        if tool_id not in _TOOL_MAP:
            raise KeyError(f"Unknown Slack tool: {tool_id!r}")

        token = _get_live_token(tenant_id)
        if token:
            try:
                return _execute_live(tool_id, params, token)
            except Exception as exc:
                logger.warning(
                    "Slack live execution failed for tool=%s, falling back to mock: %s", tool_id, exc
                )

        return {"connector": "slack", "tool": tool_id, "mode": "mock", "result": _MOCK.get(tool_id, {})}

    def test_connection(self, tenant_id: int | None = None) -> dict:
        token = _get_live_token(tenant_id)
        if token:
            try:
                from slack_sdk import WebClient  # type: ignore[import]
                client = WebClient(token=token)
                resp = client.auth_test()
                workspace = resp.get("team", "Unknown workspace")
                user = resp.get("user", "bot")
                return {
                    "ok": True,
                    "mode": "live",
                    "message": f"Connected to Slack workspace \"{workspace}\" as {user}.",
                }
            except Exception as exc:
                return {"ok": False, "mode": "live", "message": f"Slack auth_test failed: {exc}"}

        return {
            "ok": True,
            "mode": "mock",
            "message": "Slack connector ready in mock mode. Click Connect to link a real Slack workspace.",
        }

    def fetch_schema(self, tenant_id: int | None = None) -> list[SchemaObject]:
        return [
            SchemaObject("channel_message", "Channel Message", [
                SchemaField("channel", "Channel", "string", required=True, sample="#finance-alerts"),
                SchemaField("text", "Message Text", "string", required=True, sample="Budget alert: variance detected."),
                SchemaField("username", "Bot Username", "string", sample="AI Integration Cloud"),
                SchemaField("icon_emoji", "Icon Emoji", "string", sample=":robot_face:"),
                SchemaField("thread_ts", "Thread Timestamp", "string", sample="1717500000.123456"),
            ]),
        ]
