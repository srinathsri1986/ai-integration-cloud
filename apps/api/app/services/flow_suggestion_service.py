import re
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.core.config import get_settings
from app.models.audit import AuditLogEntry
from app.models.flows import (
    FlowDefinitionUpsertRequest,
    FlowSuggestionRequest,
    FlowSuggestionResponse,
    FlowTriggerType,
)
from app.models.llm import AIProvider
from app.services.audit_service import audit_service
from app.services.llm_provider import LLMProvider, LLMProviderError, make_llm_provider


APPROVED_FLOW_TOOLS = [
    # ── Generic integration actions ──────────────────────────────────────────
    "connector.schedule_trigger",
    "connector.webhook_trigger",
    "connector.fetch_records",
    "connector.search_records",
    "connector.upsert_record",
    "connector.create_record",
    "connector.update_record",
    "connector.transform_payload",
    "connector.send_notification",
    "connector.audit_log",
    "connector.retry_handler",
    # ── CFO / NetSuite specialised actions ───────────────────────────────────
    "cfo.dashboard_summary",
    "cfo.pl_vs_budget",
    "cfo.yoy_comparison",
    "cfo.subsidiary_drilldown",
    "cfo.running_projects",
    "cfo.overdue_projects_by_account_manager",
    "orchestrator.query",
]

# ── Connector detection ──────────────────────────────────────────────────────

_KNOWN_CONNECTORS: dict[str, str] = {
    "netsuite": "netsuite",
    "net suite": "netsuite",
    "salesforce": "salesforce",
    "sfdc": "salesforce",
    "sap": "sap",
    "oracle": "oracle",
    "servicenow": "servicenow",
    "service now": "servicenow",
    "hubspot": "hubspot",
    "hub spot": "hubspot",
    "workday": "workday",
    "slack": "slack",
    "sftp": "sftp",
    "rest api": "rest-api",
    "rest-api": "rest-api",
    "postgres": "postgres",
    "postgresql": "postgres",
    "mysql": "mysql",
}

_HOURLY_RE    = re.compile(r"every\s+hour|hourly|each\s+hour",        re.IGNORECASE)
_MINUTE_RE    = re.compile(r"every\s+(\d+)\s*min",                    re.IGNORECASE)
_DAILY_RE     = re.compile(r"every\s+day|daily|nightly",              re.IGNORECASE)
_WEEKLY_RE    = re.compile(r"every\s+week|weekly",                    re.IGNORECASE)
_WEBHOOK_RE   = re.compile(
    r"when\s+(?:a\s+|an\s+|the\s+)?\w+\s+(is\s+)?(created|updated|changed|modified|deleted|triggered)",
    re.IGNORECASE,
)

_CFO_KEYWORDS = [
    "cfo", "p/l", "pl vs", "profit and loss", "budget", "yoy",
    "year over year", "year-over-year", "subsidiary", "overdue projects",
    "finance", "financial report", "dashboard summary",
]

_OBJECT_KEYWORDS: dict[str, str] = {
    "customer": "customers",
    "account": "accounts",
    "vendor": "vendors",
    "invoice": "invoices",
    "order": "orders",
    "contact": "contacts",
    "product": "products",
    "item": "items",
    "employee": "employees",
    "ticket": "tickets",
    "case": "cases",
    "lead": "leads",
    "opportunity": "opportunities",
}


def _detect_connector_pair(prompt: str) -> tuple[str, str]:
    """Return (source_connector_id, target_connector_id) in the order they appear in the prompt.

    Uses first-occurrence position so 'SAP ... Salesforce' always yields source=sap, target=salesforce
    regardless of dict insertion order.
    """
    normalized = prompt.lower()
    # Map connector_id → earliest character position in the prompt
    first_pos: dict[str, int] = {}
    for keyword, connector_id in _KNOWN_CONNECTORS.items():
        pos = normalized.find(keyword)
        if pos != -1 and connector_id not in first_pos:
            first_pos[connector_id] = pos
    # Sort by appearance order
    ordered = [cid for cid, _ in sorted(first_pos.items(), key=lambda kv: kv[1])]
    if len(ordered) >= 2:
        return ordered[0], ordered[1]
    if len(ordered) == 1:
        return ordered[0], "target-system"
    return "source-system", "target-system"


def _detect_trigger(prompt: str) -> tuple[FlowTriggerType, str | None]:
    """Return (trigger_type, cron_expression_or_None) from the NL prompt."""
    if _WEBHOOK_RE.search(prompt):
        return "webhook", None
    if _HOURLY_RE.search(prompt):
        return "schedule", "0 * * * *"
    m = _MINUTE_RE.search(prompt)
    if m:
        mins = int(m.group(1))
        if 1 <= mins <= 59:
            return "schedule", f"*/{mins} * * * *"
    if _DAILY_RE.search(prompt):
        return "schedule", "0 0 * * *"
    if _WEEKLY_RE.search(prompt):
        return "schedule", "0 0 * * 0"
    if any(kw in prompt.lower() for kw in ["monthly", "month"]):
        return "schedule", "0 0 1 * *"
    if "schedule" in prompt.lower():
        return "schedule", "0 * * * *"
    return "manual", None


@dataclass(frozen=True)
class FlowSuggestionMetadata:
    provider: str
    model: str | None
    fallback_used: bool
    model_call_attempted: bool
    model_call_succeeded: bool


class LiveAIRequiredError(RuntimeError):
    pass


class FlowSuggestionService:
    def __init__(
        self,
        ai_provider: AIProvider | None = None,
        model_name: str | None = None,
        llm_provider: LLMProvider | None = None,
        openai_api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.ai_provider: AIProvider = ai_provider or settings.ai_provider  # type: ignore[assignment]
        self.model_name = model_name or self._default_model_name()
        self.openai_api_key = openai_api_key if openai_api_key is not None else settings.openai_api_key
        self.llm_provider = llm_provider or make_llm_provider(
            provider=self.ai_provider,
            model_name=self.model_name,
            openai_api_key=self.openai_api_key,
            ollama_base_url=settings.ollama_base_url,
            ollama_timeout_seconds=settings.ollama_timeout_seconds,
            # Flow generation requires reasoning over NL intent → multi-step workflow structure.
            ollama_think=True,
        )

    def suggest(self, request: FlowSuggestionRequest) -> FlowSuggestionResponse:
        request_id = str(uuid4())
        started = perf_counter()
        success = False
        failure_reason: str | None = None
        metadata = FlowSuggestionMetadata(
            provider="template",
            model=None,
            fallback_used=False,
            model_call_attempted=False,
            model_call_succeeded=False,
        )

        try:
            suggested_flow, rationale, metadata = self._suggest_flow(request)
            success = True
            return FlowSuggestionResponse(
                prompt=request.prompt,
                suggestedFlow=suggested_flow,
                rationale=rationale,
                suggestionProvider=metadata.provider,
                suggestionModel=metadata.model,
                suggestionGenerated=True,
                suggestionFallbackUsed=metadata.fallback_used,
                modelCallAttempted=metadata.model_call_attempted,
                modelCallSucceeded=metadata.model_call_succeeded,
            )
        except Exception as exc:
            failure_reason = exc.__class__.__name__
            raise
        finally:
            latency_ms = int((perf_counter() - started) * 1000)
            audit_service.record(
                AuditLogEntry(
                    timestamp=datetime.now(UTC).isoformat(),
                    requestId=request_id,
                    user="local-dev-user",
                    channel="web",
                    question=request.prompt,
                    detectedIntent="FLOW_SUGGESTION",
                    confidence=1,
                    toolsUsed=APPROVED_FLOW_TOOLS,
                    endpointCalled="/api/v1/flows/suggestions",
                    fallbackUsed=metadata.fallback_used,
                    success=success,
                    failureReason=failure_reason,
                    latencyMs=latency_ms,
                    aiProvider=metadata.provider,
                    aiMode=self._ai_mode_for_provider(metadata.provider),
                    modelName=metadata.model,
                    modelCallAttempted=metadata.model_call_attempted,
                    modelCallSucceeded=metadata.model_call_succeeded,
                    usedFallbackRouter=metadata.fallback_used,
                    narrativeProvider="none",
                    narrativeModel=None,
                    narrativeGenerated=False,
                    narrativeFallbackUsed=False,
                )
            )

    def _suggest_flow(
        self,
        request: FlowSuggestionRequest,
    ) -> tuple[FlowDefinitionUpsertRequest, str, FlowSuggestionMetadata]:
        prompt = request.prompt
        if self.ai_provider == "disabled" or self.llm_provider is None:
            if request.require_live_ai:
                raise LiveAIRequiredError("Live AI was requested, but no live AI provider is configured.")
            return (
                self._template_flow(prompt),
                "Template planner created a governed draft using approved integration actions.",
                FlowSuggestionMetadata(
                    provider="template",
                    model=None,
                    fallback_used=False,
                    model_call_attempted=False,
                    model_call_succeeded=False,
                ),
            )

        source_connector, target_connector = _detect_connector_pair(prompt)
        context = {
            "prompt": prompt,
            "sourceConnector": source_connector,
            "targetConnector": target_connector,
            "approvedTools": APPROVED_FLOW_TOOLS,
            "policy": (
                "Suggest a draft only. Do not execute, publish, save automatically, generate "
                "SQL, SuiteQL, raw queries, credentials, secrets, or arbitrary code."
            ),
        }

        try:
            result = self.llm_provider.generate_flow_suggestion(context)
            suggested_flow = FlowDefinitionUpsertRequest.model_validate(result.suggested_flow)
            return (
                suggested_flow,
                result.rationale,
                FlowSuggestionMetadata(
                    provider=result.provider_name,
                    model=result.model_name,
                    fallback_used=False,
                    model_call_attempted=result.model_call_attempted,
                    model_call_succeeded=result.model_call_succeeded,
                ),
            )
        except Exception as exc:
            attempted = exc.model_call_attempted if isinstance(exc, LLMProviderError) else False
            succeeded = exc.model_call_succeeded if isinstance(exc, LLMProviderError) else False
            if request.require_live_ai and self.ai_provider in {"ollama", "openai"}:
                raise LiveAIRequiredError(
                    "Live AI was requested, but the configured provider returned invalid or unavailable output."
                ) from exc
            return (
                self._template_flow(prompt),
                "AI output was unavailable or invalid, so a deterministic governed draft was used.",
                FlowSuggestionMetadata(
                    provider=self.ai_provider,
                    model=self.model_name,
                    fallback_used=True,
                    model_call_attempted=attempted,
                    model_call_succeeded=succeeded,
                ),
            )

    def _template_flow(self, prompt: str) -> FlowDefinitionUpsertRequest:
        """Route to CFO template for finance prompts; generic integration template otherwise."""
        normalized = prompt.lower()
        if any(kw in normalized for kw in _CFO_KEYWORDS):
            return self._template_cfo_flow(prompt)
        return self._template_integration_flow(prompt)

    def _template_integration_flow(self, prompt: str) -> FlowDefinitionUpsertRequest:
        """Generic iPaaS integration template: trigger → fetch → transform → search → upsert → audit."""
        source_connector, target_connector = _detect_connector_pair(prompt)
        trigger_type, trigger_cron = _detect_trigger(prompt)

        source_label = source_connector.replace("-", " ").title()
        target_label = target_connector.replace("-", " ").title()

        # Detect business object from prompt keywords
        object_label = "records"
        for kw, label in _OBJECT_KEYWORDS.items():
            if kw in prompt.lower():
                object_label = label
                break

        steps: list[dict] = []

        # Step 1: Trigger (only for scheduled / webhook flows)
        if trigger_type == "schedule":
            steps.append({
                "id": "trigger",
                "name": "Schedule Trigger",
                "description": (
                    f"Execute on schedule ({trigger_cron}) to start "
                    f"{source_label} {object_label} sync."
                ),
                "approvedTool": "connector.schedule_trigger",
            })
        elif trigger_type == "webhook":
            steps.append({
                "id": "trigger",
                "name": "Webhook Trigger",
                "description": f"Listen for {source_label} event to trigger the integration.",
                "approvedTool": "connector.webhook_trigger",
            })

        # Step 2: Fetch from source
        steps.append({
            "id": "fetch-source",
            "name": f"Fetch {source_label} {object_label.title()}",
            "description": (
                f"Fetch {object_label} from {source_label} using the approved connector."
            ),
            "approvedTool": "connector.fetch_records",
        })

        # Step 3: Transform payload
        steps.append({
            "id": "transform",
            "name": "Transform Payload",
            "description": (
                f"Apply field mappings and type coercions to prepare "
                f"{object_label} for {target_label}."
            ),
            "approvedTool": "connector.transform_payload",
        })

        # Step 4: Search target (deduplication)
        steps.append({
            "id": "search-target",
            "name": f"Search {target_label}",
            "description": (
                f"Search {target_label} for existing {object_label} to enable deduplication."
            ),
            "approvedTool": "connector.search_records",
        })

        # Step 5: Upsert to target
        steps.append({
            "id": "upsert-target",
            "name": f"Upsert {target_label} {object_label.title()}",
            "description": f"Create or update {object_label} in {target_label} via governed upsert.",
            "approvedTool": "connector.upsert_record",
        })

        # Step 6: Audit + retry
        steps.append({
            "id": "audit-log",
            "name": "Audit & Retry",
            "description": (
                "Write an immutable audit log entry and apply retry policy on transient failures."
            ),
            "approvedTool": "connector.audit_log",
        })

        # flow_id slug must match ^[a-z0-9-]+$
        flow_id = f"ai-drafted-{source_connector}-to-{target_connector}"
        target_module = f"{target_connector}-{object_label}"

        return FlowDefinitionUpsertRequest(
            flowId=flow_id,
            name=f"{source_label} → {target_label} {object_label.title()} Sync",
            description=(
                f"Draft integration generated from a natural-language request. "
                f"Syncs {object_label} from {source_label} to {target_label} "
                f"using approved connector actions only."
            ),
            sourceConnector=source_connector,
            targetModule=target_module,
            targetConnector=target_connector,
            status="draft",
            triggerType=trigger_type,
            triggerCron=trigger_cron,
            steps=steps[:8],
        )

    def _template_cfo_flow(self, prompt: str) -> FlowDefinitionUpsertRequest:
        """Original CFO-specific template preserved for finance / NetSuite analytics prompts."""
        normalized = prompt.lower()
        steps: list[dict] = [{
            "id": "load-cfo-summary",
            "name": "Load CFO summary",
            "description": "Load approved CFO dashboard summary data.",
            "approvedTool": "cfo.dashboard_summary",
        }]

        if any(term in normalized for term in ["budget", "p/l", "profit and loss", "variance"]):
            steps.append({
                "id": "compare-pl-budget",
                "name": "Compare P/L vs budget",
                "description": "Compare approved P/L actuals against budget.",
                "approvedTool": "cfo.pl_vs_budget",
            })

        if any(term in normalized for term in ["overdue", "risk", "late", "project"]):
            steps.append({
                "id": "summarize-overdue-projects",
                "name": "Summarize overdue projects",
                "description": "Summarize overdue project exposure by account manager.",
                "approvedTool": "cfo.overdue_projects_by_account_manager",
            })

        if any(term in normalized for term in ["subsidiary", "drilldown", "drill down"]):
            steps.append({
                "id": "load-subsidiary-drilldown",
                "name": "Load subsidiary drilldown",
                "description": "Load approved subsidiary operating performance data.",
                "approvedTool": "cfo.subsidiary_drilldown",
            })

        if "yoy" in normalized or "year over year" in normalized or "year-over-year" in normalized:
            steps.append({
                "id": "compare-yoy",
                "name": "Compare YoY performance",
                "description": "Compare approved current year and prior year metrics.",
                "approvedTool": "cfo.yoy_comparison",
            })

        if any(term in normalized for term in ["narrative", "summary", "ai", "cfo"]):
            steps.append({
                "id": "route-approved-cfo-question",
                "name": "Route approved CFO question",
                "description": "Route a governed CFO question without direct model tool execution.",
                "approvedTool": "orchestrator.query",
            })

        if "monthly" in normalized or "schedule" in normalized:
            trigger_type: FlowTriggerType = "schedule"
            trigger_cron: str | None = "0 0 1 * *"
        else:
            trigger_type = "manual"
            trigger_cron = None

        return FlowDefinitionUpsertRequest(
            flowId="ai-drafted-cfo-flow",
            name="AI drafted CFO flow",
            description=(
                "Draft CFO orchestration generated from a natural-language request using "
                "approved NetSuite actions only."
            ),
            sourceConnector="netsuite",
            targetModule="cfo_dashboard",
            status="draft",
            triggerType=trigger_type,
            triggerCron=trigger_cron,
            steps=steps[:8],
        )

    def _default_model_name(self) -> str:
        settings = get_settings()

        if self.ai_provider == "openai":
            return settings.openai_model

        if self.ai_provider == "ollama":
            return settings.ollama_model

        return "mock-flow-suggestion-v0"

    def _ai_mode_for_provider(self, provider_name: str) -> str:
        if provider_name == "mock":
            return "mock_llm"

        if provider_name in {"openai", "ollama"}:
            return provider_name

        if provider_name == "template":
            return "rule_based"

        return "disabled"


flow_suggestion_service = FlowSuggestionService()
