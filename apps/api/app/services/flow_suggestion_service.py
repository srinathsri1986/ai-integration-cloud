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
)
from app.models.llm import AIProvider
from app.services.audit_service import audit_service
from app.services.llm_provider import LLMProvider, LLMProviderError, make_llm_provider


APPROVED_FLOW_TOOLS = [
    "cfo.dashboard_summary",
    "cfo.pl_vs_budget",
    "cfo.yoy_comparison",
    "cfo.subsidiary_drilldown",
    "cfo.running_projects",
    "cfo.overdue_projects_by_account_manager",
    "orchestrator.query",
]


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
                "Template planner created a governed draft using approved NetSuite CFO actions.",
                FlowSuggestionMetadata(
                    provider="template",
                    model=None,
                    fallback_used=False,
                    model_call_attempted=False,
                    model_call_succeeded=False,
                ),
            )

        context = {
            "prompt": prompt,
            "approvedConnector": "netsuite",
            "approvedTools": APPROVED_FLOW_TOOLS,
            "policy": (
                "Suggest a draft only. Do not execute, publish, save automatically, generate "
                "SQL, SuiteQL, raw NetSuite queries, credentials, secrets, or arbitrary code."
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
        normalized = prompt.lower()
        steps = [
            {
                "id": "load-cfo-summary",
                "name": "Load CFO summary",
                "description": "Load approved CFO dashboard summary data.",
                "approvedTool": "cfo.dashboard_summary",
            }
        ]

        if any(term in normalized for term in ["budget", "p/l", "profit and loss", "variance"]):
            steps.append(
                {
                    "id": "compare-pl-budget",
                    "name": "Compare P/L vs budget",
                    "description": "Compare approved P/L actuals against budget.",
                    "approvedTool": "cfo.pl_vs_budget",
                }
            )

        if any(term in normalized for term in ["overdue", "risk", "late", "project"]):
            steps.append(
                {
                    "id": "summarize-overdue-projects",
                    "name": "Summarize overdue projects",
                    "description": "Summarize overdue project exposure by account manager.",
                    "approvedTool": "cfo.overdue_projects_by_account_manager",
                }
            )

        if "monthly" in normalized or "schedule" in normalized:
            trigger_type = "schedule_placeholder"
        else:
            trigger_type = "manual"

        if any(term in normalized for term in ["narrative", "summary", "ai", "cfo"]):
            steps.append(
                {
                    "id": "route-approved-cfo-question",
                    "name": "Route approved CFO question",
                    "description": (
                        "Route a governed CFO question without direct model tool execution."
                    ),
                    "approvedTool": "orchestrator.query",
                }
            )

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
