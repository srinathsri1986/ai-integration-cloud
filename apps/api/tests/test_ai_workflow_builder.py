"""
TDD — AI Workflow Builder: generic iPaaS integration flow suggestion

Tests cover:
  • APPROVED_FLOW_TOOLS now includes generic connector.* actions
  • _template_flow generates connector-pair integration steps (not just CFO tools)
  • Trigger detection: schedule (hourly / every-N-min / daily), webhook, manual
  • CFO prompts still fall through to CFO-specific tool set
  • All step tools are in APPROVED_FLOW_TOOLS
  • LLM context includes sourceConnector + targetConnector when ai_provider != disabled
"""

import pytest

from app.models.flows import FlowSuggestionRequest
from app.services.flow_suggestion_service import (
    APPROVED_FLOW_TOOLS,
    FlowSuggestionService,
)


# ── APPROVED_FLOW_TOOLS coverage ─────────────────────────────────────────────


class TestApprovedFlowTools:
    def test_includes_connector_fetch_records(self):
        assert "connector.fetch_records" in APPROVED_FLOW_TOOLS

    def test_includes_connector_upsert_record(self):
        assert "connector.upsert_record" in APPROVED_FLOW_TOOLS

    def test_includes_connector_transform_payload(self):
        assert "connector.transform_payload" in APPROVED_FLOW_TOOLS

    def test_includes_connector_search_records(self):
        assert "connector.search_records" in APPROVED_FLOW_TOOLS

    def test_includes_connector_schedule_trigger(self):
        assert "connector.schedule_trigger" in APPROVED_FLOW_TOOLS

    def test_includes_connector_webhook_trigger(self):
        assert "connector.webhook_trigger" in APPROVED_FLOW_TOOLS

    def test_includes_connector_audit_log(self):
        assert "connector.audit_log" in APPROVED_FLOW_TOOLS

    def test_includes_connector_retry_handler(self):
        assert "connector.retry_handler" in APPROVED_FLOW_TOOLS

    def test_cfo_tools_still_present(self):
        assert "cfo.pl_vs_budget" in APPROVED_FLOW_TOOLS
        assert "cfo.dashboard_summary" in APPROVED_FLOW_TOOLS
        assert "orchestrator.query" in APPROVED_FLOW_TOOLS


# ── Generic integration template ─────────────────────────────────────────────


class TestTemplateFlowGenericIntegration:
    def setup_method(self):
        # ai_provider="disabled" forces deterministic template path — no LLM needed
        self.svc = FlowSuggestionService(ai_provider="disabled")

    # connector pair detection
    def test_netsuite_to_salesforce_source_target(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite customers to Salesforce every hour")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.source_connector == "netsuite"
        assert flow.target_connector == "salesforce"

    def test_sap_to_servicenow_source_target(self):
        req = FlowSuggestionRequest(prompt="Push SAP vendors into ServiceNow daily")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.source_connector == "sap"
        assert flow.target_connector == "servicenow"

    def test_netsuite_to_hubspot_source_target(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite contacts to HubSpot every 30 min")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.source_connector == "netsuite"
        assert flow.target_connector == "hubspot"

    # trigger detection — schedule
    def test_trigger_schedule_hourly(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite invoices to Salesforce every hour")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.trigger_type == "schedule"
        assert flow.trigger_cron == "0 * * * *"

    def test_trigger_schedule_every_15_min(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite orders to Salesforce every 15 min")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.trigger_type == "schedule"
        assert flow.trigger_cron == "*/15 * * * *"

    def test_trigger_schedule_daily(self):
        req = FlowSuggestionRequest(prompt="Push SAP accounts to Salesforce every day")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.trigger_type == "schedule"
        assert flow.trigger_cron == "0 0 * * *"

    def test_trigger_schedule_monthly(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite customers to Salesforce monthly")
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.trigger_type == "schedule"
        assert flow.trigger_cron == "0 0 1 * *"

    # trigger detection — webhook
    def test_trigger_webhook_on_create(self):
        req = FlowSuggestionRequest(
            prompt="When a customer is created in NetSuite push to Salesforce"
        )
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.trigger_type == "webhook"
        assert flow.trigger_cron is None

    def test_trigger_webhook_on_update(self):
        req = FlowSuggestionRequest(
            prompt="When a vendor is updated in SAP sync changes to ServiceNow"
        )
        resp = self.svc.suggest(req)
        flow = resp.suggested_flow
        assert flow.trigger_type == "webhook"

    # trigger detection — manual (default)
    def test_trigger_manual_default(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite contacts to Salesforce")
        resp = self.svc.suggest(req)
        assert resp.suggested_flow.trigger_type == "manual"

    # step content
    def test_flow_has_at_least_four_steps(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite customers to Salesforce every hour")
        resp = self.svc.suggest(req)
        assert len(resp.suggested_flow.steps) >= 4

    def test_fetch_records_step_present(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite customers to Salesforce every hour")
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert "connector.fetch_records" in tools

    def test_upsert_record_step_present(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite customers to Salesforce every hour")
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert "connector.upsert_record" in tools

    def test_transform_payload_step_present(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite invoices to Salesforce every hour")
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert "connector.transform_payload" in tools

    def test_schedule_trigger_step_added_for_schedule_flow(self):
        req = FlowSuggestionRequest(prompt="Sync SAP vendors to ServiceNow daily")
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert "connector.schedule_trigger" in tools

    def test_webhook_trigger_step_added_for_webhook_flow(self):
        req = FlowSuggestionRequest(
            prompt="When an order is created in NetSuite push it to Salesforce"
        )
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert "connector.webhook_trigger" in tools

    def test_all_step_tools_are_approved(self):
        req = FlowSuggestionRequest(prompt="Sync SAP vendors to ServiceNow daily")
        resp = self.svc.suggest(req)
        for step in resp.suggested_flow.steps:
            assert step.approved_tool in APPROVED_FLOW_TOOLS, (
                f"Tool '{step.approved_tool}' is not in APPROVED_FLOW_TOOLS"
            )

    # CFO prompts still use CFO-specific tools
    def test_cfo_prompt_uses_cfo_tools(self):
        req = FlowSuggestionRequest(prompt="Generate a P/L vs budget report for the CFO")
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert any(t.startswith("cfo.") for t in tools)

    def test_budget_prompt_uses_cfo_pl_tool(self):
        req = FlowSuggestionRequest(prompt="Show me P/L variance versus budget for Q3")
        resp = self.svc.suggest(req)
        tools = [s.approved_tool for s in resp.suggested_flow.steps]
        assert "cfo.pl_vs_budget" in tools

    # flow metadata correctness
    def test_flow_id_matches_regex(self):
        import re
        req = FlowSuggestionRequest(prompt="Sync SAP accounts to Salesforce daily")
        resp = self.svc.suggest(req)
        assert re.match(r"^[a-z0-9-]+$", resp.suggested_flow.flow_id)

    def test_flow_status_is_draft(self):
        req = FlowSuggestionRequest(prompt="Sync NetSuite contacts to Salesforce hourly")
        resp = self.svc.suggest(req)
        assert resp.suggested_flow.status == "draft"
