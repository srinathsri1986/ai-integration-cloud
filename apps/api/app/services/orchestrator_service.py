from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from app.core.config import get_settings
from app.models.audit import AuditLogEntry
from app.models.llm import AIProviderMode, AIRoutingMode
from app.models.orchestrator import (
    OrchestratorIntent,
    OrchestratorQueryRequest,
    OrchestratorQueryResponse,
)
from app.services.audit_service import audit_service
from app.services.cfo_service import CfoService
from app.services.llm_provider import LLMProvider, make_llm_provider


@dataclass(frozen=True)
class IntentMatch:
    confidence: float
    intent: OrchestratorIntent
    ai_provider: str = "rule_based"
    ai_mode: AIRoutingMode = "rule_based"
    model_name: str | None = None
    used_fallback_router: bool = False


class OrchestratorService:
    def __init__(
        self,
        cfo_service: CfoService | None = None,
        ai_provider_mode: AIProviderMode | None = None,
        model_name: str | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        settings = get_settings()
        self.cfo_service = cfo_service or CfoService()
        self.ai_provider_mode: AIProviderMode = (
            ai_provider_mode or settings.ai_provider_mode  # type: ignore[assignment]
        )
        self.model_name = model_name or settings.ai_model_name
        self.llm_provider = llm_provider or make_llm_provider(
            mode=self.ai_provider_mode,
            model_name=self.model_name,
        )

    def route_intent(self, question: str) -> IntentMatch:
        normalized = question.lower()

        if any(term in normalized for term in ["overdue", "late", "past due"]):
            return IntentMatch(0.92, OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER)

        if any(term in normalized for term in ["running project", "active project", "project status"]):
            return IntentMatch(0.88, OrchestratorIntent.RUNNING_PROJECTS)

        if any(term in normalized for term in ["subsidiary", "drilldown", "drill down", "emea", "na"]):
            return IntentMatch(0.86, OrchestratorIntent.SUBSIDIARY_DRILLDOWN)

        if any(term in normalized for term in ["yoy", "year over year", "year-over-year"]):
            return IntentMatch(0.9, OrchestratorIntent.YOY_COMPARISON)

        if any(term in normalized for term in ["budget", "plan", "p/l", "profit and loss", "actuals"]):
            return IntentMatch(0.89, OrchestratorIntent.PL_VS_BUDGET)

        if any(term in normalized for term in ["dashboard", "summary", "kpi", "cash", "receivables"]):
            return IntentMatch(0.84, OrchestratorIntent.CFO_DASHBOARD_SUMMARY)

        return IntentMatch(0.2, OrchestratorIntent.UNKNOWN)

    def extract_intent(self, question: str) -> IntentMatch:
        if self.ai_provider_mode == "disabled":
            rule_match = self.route_intent(question)
            return IntentMatch(
                confidence=rule_match.confidence,
                intent=rule_match.intent,
                ai_provider="none",
                ai_mode="rule_based",
                model_name=None,
                used_fallback_router=False,
            )

        if self.ai_provider_mode in {"openai_placeholder", "anthropic_placeholder"}:
            rule_match = self.route_intent(question)
            return IntentMatch(
                confidence=rule_match.confidence,
                intent=rule_match.intent,
                ai_provider=self.ai_provider_mode.replace("_placeholder", ""),
                ai_mode="disabled",
                model_name=self.model_name,
                used_fallback_router=True,
            )

        try:
            if self.llm_provider is None:
                raise RuntimeError("No LLM provider configured.")

            provider_match = self.llm_provider.extract_intent(question)
            return IntentMatch(
                confidence=provider_match.confidence,
                intent=provider_match.intent,
                ai_provider=provider_match.provider_name,
                ai_mode="mock_llm",
                model_name=provider_match.model_name,
                used_fallback_router=False,
            )
        except Exception:
            rule_match = self.route_intent(question)
            return IntentMatch(
                confidence=rule_match.confidence,
                intent=rule_match.intent,
                ai_provider="mock",
                ai_mode="mock_llm",
                model_name=self.model_name,
                used_fallback_router=True,
            )

    def query(self, request: OrchestratorQueryRequest) -> OrchestratorQueryResponse:
        request_id = str(uuid4())
        started = perf_counter()
        match = self.extract_intent(request.question)
        period = request.period_range or "2026-Q1"
        subsidiary = request.subsidiary or "NA"
        endpoint_called = "/api/v1/orchestrator/query"
        tools: list[str] = []
        success = False
        failure_reason: str | None = None

        try:
            if match.intent == OrchestratorIntent.CFO_DASHBOARD_SUMMARY:
                endpoint_called = "/api/v1/cfo/dashboard-summary"
                data = self.cfo_service.dashboard_summary().model_dump()
                tools = ["cfo.dashboard_summary"]
                summary = "CFO dashboard summary retrieved from approved mock CFO service data."
            elif match.intent == OrchestratorIntent.PL_VS_BUDGET:
                endpoint_called = "/api/v1/cfo/pl-vs-budget"
                data = self.cfo_service.pl_vs_budget(
                    period=period,
                    subsidiary_id=subsidiary,
                ).model_dump()
                tools = ["cfo.pl_vs_budget"]
                summary = f"P/L vs budget retrieved for {period} and subsidiary {subsidiary}."
            elif match.intent == OrchestratorIntent.YOY_COMPARISON:
                endpoint_called = "/api/v1/cfo/yoy-comparison"
                data = self.cfo_service.yoy_comparison(
                    current_year=2026,
                    prior_year=2025,
                    subsidiary_id=subsidiary,
                ).model_dump()
                tools = ["cfo.yoy_comparison"]
                summary = f"YoY comparison retrieved for 2026 vs 2025 and subsidiary {subsidiary}."
            elif match.intent == OrchestratorIntent.SUBSIDIARY_DRILLDOWN:
                endpoint_called = "/api/v1/cfo/subsidiary-drilldown"
                data = self.cfo_service.subsidiary_drilldown(
                    period=period,
                    subsidiary_id=request.subsidiary or "EMEA",
                ).model_dump()
                tools = ["cfo.subsidiary_drilldown"]
                summary = f"Subsidiary drilldown retrieved for {period}."
            elif match.intent == OrchestratorIntent.RUNNING_PROJECTS:
                endpoint_called = "/api/v1/cfo/running-projects"
                data = self.cfo_service.running_projects(
                    subsidiary_id=request.subsidiary,
                ).model_dump()
                tools = ["cfo.running_projects"]
                summary = "Running project financials retrieved from approved mock CFO service data."
            elif match.intent == OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER:
                endpoint_called = "/api/v1/cfo/overdue-projects/by-account-manager"
                data = self.cfo_service.overdue_projects_by_account_manager().model_dump()
                tools = ["cfo.overdue_projects_by_account_manager"]
                summary = (
                    "Overdue projects summarized by account manager from approved mock CFO "
                    "service data."
                )
            else:
                data = {"message": "No supported CFO intent matched this question."}
                summary = "I could not confidently map the question to a supported CFO workflow."

            success = True
            return OrchestratorQueryResponse(
                detectedIntent=match.intent,
                confidence=match.confidence,
                toolsUsed=tools,
                data=data,
                executiveSummary=summary,
                fallbackUsed=False,
                aiProvider=match.ai_provider,
                aiMode=match.ai_mode,
                modelName=match.model_name,
                usedFallbackRouter=match.used_fallback_router,
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
                    question=request.question,
                    detectedIntent=match.intent.value,
                    confidence=match.confidence,
                    toolsUsed=tools,
                    endpointCalled=endpoint_called,
                    fallbackUsed=False,
                    success=success,
                    failureReason=failure_reason,
                    latencyMs=latency_ms,
                    aiProvider=match.ai_provider,
                    aiMode=match.ai_mode,
                    modelName=match.model_name,
                    usedFallbackRouter=match.used_fallback_router,
                )
            )
