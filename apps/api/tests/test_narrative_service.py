from app.models.orchestrator import OrchestratorIntent
from app.services.llm_provider import LLMNarrativeResult
from app.services.narrative_service import NarrativeService


class SuccessfulNarrativeProvider:
    provider_name = "ollama"
    model_name = "qwen2.5-coder:7b"

    def generate_narrative(self, context: dict) -> LLMNarrativeResult:
        assert context["sourcePolicy"].startswith("Approved structured CFO service output only")
        assert "highlights" in context
        return LLMNarrativeResult(
            narrative="Approved CFO data shows favorable budget performance and manageable variance risk.",
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )


class FailingNarrativeProvider:
    provider_name = "openai"
    model_name = "gpt-test"

    def generate_narrative(self, context: dict) -> LLMNarrativeResult:
        raise RuntimeError("narrative provider failed")


def test_disabled_provider_uses_deterministic_template() -> None:
    service = NarrativeService(
        ai_provider="disabled",
        model_name=None,
        llm_provider=None,
    )

    result = service.generate(
        intent=OrchestratorIntent.UNKNOWN,
        tools_used=[],
        approved_data={"message": "No supported CFO intent matched this question."},
        deterministic_summary="I could not confidently map the question to a supported CFO workflow.",
    )

    assert result.provider == "template"
    assert result.model is None
    assert result.generated is True
    assert result.fallback_used is False
    assert "supported CFO intent" in result.narrative


def test_successful_provider_uses_approved_summarized_context() -> None:
    service = NarrativeService(
        ai_provider="ollama",
        model_name="qwen2.5-coder:7b",
        llm_provider=SuccessfulNarrativeProvider(),
    )

    result = service.generate(
        intent=OrchestratorIntent.PL_VS_BUDGET,
        tools_used=["cfo.pl_vs_budget"],
        approved_data={
            "lines": [
                {
                    "line": "Revenue",
                    "actual": 8270000,
                    "budget": 7950000,
                    "variance": 320000,
                    "variance_pct": 4.03,
                }
            ]
        },
        deterministic_summary="P/L vs budget retrieved for 2026-Q1 and subsidiary NA.",
    )

    assert result.provider == "ollama"
    assert result.model == "qwen2.5-coder:7b"
    assert result.generated is True
    assert result.fallback_used is False
    assert "Approved CFO data" in result.narrative


def test_provider_failure_uses_template_fallback() -> None:
    service = NarrativeService(
        ai_provider="openai",
        model_name="gpt-test",
        llm_provider=FailingNarrativeProvider(),
    )

    result = service.generate(
        intent=OrchestratorIntent.RUNNING_PROJECTS,
        tools_used=["cfo.running_projects"],
        approved_data={
            "projects": [
                {
                    "project_name": "Revenue Automation Rollout",
                    "status": "at_risk",
                    "forecast_cost": 398000,
                    "budget": 420000,
                }
            ]
        },
        deterministic_summary="Running project financials retrieved from approved mock CFO service data.",
    )

    assert result.provider == "openai"
    assert result.model == "gpt-test"
    assert result.generated is True
    assert result.fallback_used is True
    assert "Revenue Automation Rollout" in result.narrative
