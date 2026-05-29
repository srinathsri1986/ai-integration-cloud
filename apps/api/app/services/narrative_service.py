from dataclasses import dataclass
from typing import Any

from app.models.llm import AIProvider
from app.models.orchestrator import OrchestratorIntent
from app.services.llm_provider import LLMProvider


@dataclass(frozen=True)
class NarrativeResult:
    narrative: str
    provider: str
    model: str | None
    generated: bool
    fallback_used: bool


class NarrativeService:
    def __init__(
        self,
        ai_provider: AIProvider,
        model_name: str | None,
        llm_provider: LLMProvider | None,
    ) -> None:
        self.ai_provider = ai_provider
        self.model_name = model_name
        self.llm_provider = llm_provider

    def generate(
        self,
        *,
        intent: OrchestratorIntent,
        tools_used: list[str],
        approved_data: dict[str, Any],
        deterministic_summary: str,
    ) -> NarrativeResult:
        context = self._build_context(
            intent=intent,
            tools_used=tools_used,
            approved_data=approved_data,
            deterministic_summary=deterministic_summary,
        )

        if self.ai_provider == "disabled" or self.llm_provider is None:
            return NarrativeResult(
                narrative=self._template_narrative(context),
                provider="template",
                model=None,
                generated=True,
                fallback_used=False,
            )

        try:
            result = self.llm_provider.generate_narrative(context)
            return NarrativeResult(
                narrative=result.narrative,
                provider=result.provider_name,
                model=result.model_name,
                generated=True,
                fallback_used=False,
            )
        except Exception:
            return NarrativeResult(
                narrative=self._template_narrative(context),
                provider=self.ai_provider,
                model=self.model_name,
                generated=True,
                fallback_used=True,
            )

    def _build_context(
        self,
        *,
        intent: OrchestratorIntent,
        tools_used: list[str],
        approved_data: dict[str, Any],
        deterministic_summary: str,
    ) -> dict[str, Any]:
        return {
            "intent": intent.value,
            "toolsUsed": tools_used,
            "summary": deterministic_summary,
            "highlights": self._highlights_for_intent(intent, approved_data),
            "sourcePolicy": (
                "Approved structured CFO service output only; no credentials, raw "
                "transactions, SQL, SuiteQL, or raw NetSuite access."
            ),
        }

    def _highlights_for_intent(
        self,
        intent: OrchestratorIntent,
        data: dict[str, Any],
    ) -> list[str]:
        if intent == OrchestratorIntent.PL_VS_BUDGET:
            return [
                (
                    f"{line['line']} actual {line['actual']} vs budget {line['budget']} "
                    f"with variance {line['variance']} ({line['variance_pct']}%)."
                )
                for line in data.get("lines", [])[:3]
            ]

        if intent == OrchestratorIntent.YOY_COMPARISON:
            return [
                (
                    f"{line['metric']} changed {line['change']} "
                    f"({line['change_pct']}%) vs prior year."
                )
                for line in data.get("lines", [])[:3]
            ]

        if intent == OrchestratorIntent.SUBSIDIARY_DRILLDOWN:
            return [
                (
                    f"{line['subsidiary_name']} {line['department']} operating income is "
                    f"{line['operating_income']} on revenue {line['revenue']}."
                )
                for line in data.get("lines", [])[:3]
            ]

        if intent == OrchestratorIntent.RUNNING_PROJECTS:
            return [
                (
                    f"{project['project_name']} is {project['status']} with forecast cost "
                    f"{project['forecast_cost']} against budget {project['budget']}."
                )
                for project in data.get("projects", [])[:3]
            ]

        if intent == OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER:
            return [
                (
                    f"{manager['account_manager']} has {manager['overdue_project_count']} "
                    f"overdue projects totaling {manager['total_overdue_amount']}."
                )
                for manager in data.get("managers", [])[:3]
            ]

        if intent == OrchestratorIntent.CFO_DASHBOARD_SUMMARY:
            kpi_highlights = [
                f"{kpi['label']} is {kpi['value']} with {kpi['trend']} trend."
                for kpi in data.get("kpis", [])[:3]
            ]
            return [
                f"Cash position is {data.get('cash_position', {}).get('amount')} {data.get('cash_position', {}).get('currency')}.",
                f"Monthly revenue is {data.get('monthly_revenue', {}).get('amount')} {data.get('monthly_revenue', {}).get('currency')}.",
                *kpi_highlights,
            ]

        return ["No supported CFO intent matched this question."]

    def _template_narrative(self, context: dict[str, Any]) -> str:
        highlights = context.get("highlights", [])
        if not highlights:
            return context["summary"]

        first = highlights[0]
        second = f" {highlights[1]}" if len(highlights) > 1 else ""
        return (
            f"{context['summary']} {first}{second} Review the highlighted variance or risk "
            "with the finance owner before taking action."
        )[:900]
