from dataclasses import dataclass
from typing import Protocol

from app.models.llm import AIProviderMode
from app.models.orchestrator import OrchestratorIntent


@dataclass(frozen=True)
class LLMIntentResult:
    confidence: float
    intent: OrchestratorIntent
    model_name: str
    provider_name: str


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    def extract_intent(self, question: str) -> LLMIntentResult:
        """Return a supported CFO intent without executing tools or raw queries."""


class MockLLMProvider:
    provider_name = "mock"

    def __init__(self, model_name: str = "mock-cfo-intent-v0") -> None:
        self.model_name = model_name

    def extract_intent(self, question: str) -> LLMIntentResult:
        normalized = question.lower()

        if "mock_provider_fail" in normalized:
            raise RuntimeError("Mock provider failure requested for fallback coverage.")

        if any(term in normalized for term in ["overdue", "late", "past due"]):
            intent = OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER
            confidence = 0.94
        elif any(term in normalized for term in ["running project", "active project", "project status"]):
            intent = OrchestratorIntent.RUNNING_PROJECTS
            confidence = 0.9
        elif any(term in normalized for term in ["subsidiary", "drilldown", "drill down", "emea", "na"]):
            intent = OrchestratorIntent.SUBSIDIARY_DRILLDOWN
            confidence = 0.89
        elif any(term in normalized for term in ["yoy", "year over year", "year-over-year"]):
            intent = OrchestratorIntent.YOY_COMPARISON
            confidence = 0.92
        elif any(term in normalized for term in ["budget", "plan", "p/l", "profit and loss", "actuals"]):
            intent = OrchestratorIntent.PL_VS_BUDGET
            confidence = 0.91
        elif any(term in normalized for term in ["dashboard", "summary", "kpi", "cash", "receivables"]):
            intent = OrchestratorIntent.CFO_DASHBOARD_SUMMARY
            confidence = 0.87
        else:
            intent = OrchestratorIntent.UNKNOWN
            confidence = 0.25

        return LLMIntentResult(
            confidence=confidence,
            intent=intent,
            model_name=self.model_name,
            provider_name=self.provider_name,
        )


def make_llm_provider(mode: AIProviderMode, model_name: str) -> LLMProvider | None:
    if mode == "mock":
        return MockLLMProvider(model_name=model_name)

    return None
