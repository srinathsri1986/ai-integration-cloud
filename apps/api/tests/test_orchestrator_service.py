from app.models.orchestrator import OrchestratorIntent, OrchestratorQueryRequest
from app.services.llm_provider import LLMIntentResult
from app.services.orchestrator_service import OrchestratorService


class FailingLLMProvider:
    provider_name = "mock"
    model_name = "failing-mock"

    def extract_intent(self, question: str) -> LLMIntentResult:
        raise RuntimeError("Provider failed")


def test_routes_pl_vs_budget_intent() -> None:
    service = OrchestratorService()

    match = service.route_intent("Show me P/L actuals vs budget for Q1")

    assert match.intent == OrchestratorIntent.PL_VS_BUDGET
    assert match.confidence > 0.8


def test_routes_overdue_projects_intent() -> None:
    service = OrchestratorService()

    match = service.route_intent("Which projects are overdue by account manager?")

    assert match.intent == OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER


def test_routes_unknown_intent() -> None:
    service = OrchestratorService()

    match = service.route_intent("Tell me about customer sentiment on social media")

    assert match.intent == OrchestratorIntent.UNKNOWN
    assert match.confidence < 0.5


def test_unknown_intent_does_not_use_tools() -> None:
    service = OrchestratorService()

    response = service.query(
        OrchestratorQueryRequest(question="Can you run select * from transaction?")
    )

    assert response.detected_intent == OrchestratorIntent.UNKNOWN
    assert response.tools_used == []
    assert response.ai_mode == "rule_based"
    assert response.used_fallback_router is False


def test_default_intent_extraction_uses_rule_based_router() -> None:
    service = OrchestratorService(ai_provider_mode="disabled")

    match = service.extract_intent("Compare revenue year over year")

    assert match.intent == OrchestratorIntent.YOY_COMPARISON
    assert match.ai_provider == "none"
    assert match.ai_mode == "rule_based"
    assert match.model_name is None
    assert match.used_fallback_router is False


def test_mock_llm_intent_routing() -> None:
    service = OrchestratorService(ai_provider_mode="mock", model_name="mock-cfo-intent-v0")

    response = service.query(
        OrchestratorQueryRequest(question="Which projects are overdue by account manager?")
    )

    assert response.detected_intent == OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER
    assert response.tools_used == ["cfo.overdue_projects_by_account_manager"]
    assert response.ai_provider == "mock"
    assert response.ai_mode == "mock_llm"
    assert response.model_name == "mock-cfo-intent-v0"
    assert response.used_fallback_router is False


def test_provider_failure_falls_back_to_rule_based_router() -> None:
    service = OrchestratorService(
        ai_provider_mode="mock",
        model_name="failing-mock",
        llm_provider=FailingLLMProvider(),
    )

    response = service.query(OrchestratorQueryRequest(question="Show me P/L vs budget for Q1"))

    assert response.detected_intent == OrchestratorIntent.PL_VS_BUDGET
    assert response.tools_used == ["cfo.pl_vs_budget"]
    assert response.ai_provider == "mock"
    assert response.ai_mode == "mock_llm"
    assert response.model_name == "failing-mock"
    assert response.used_fallback_router is True


def test_placeholder_provider_mode_uses_rule_based_fallback_without_external_call() -> None:
    service = OrchestratorService(
        ai_provider_mode="openai_placeholder",
        model_name="placeholder-model",
    )

    response = service.query(OrchestratorQueryRequest(question="Show EMEA subsidiary drilldown"))

    assert response.detected_intent == OrchestratorIntent.SUBSIDIARY_DRILLDOWN
    assert response.tools_used == ["cfo.subsidiary_drilldown"]
    assert response.ai_provider == "openai"
    assert response.ai_mode == "disabled"
    assert response.model_name == "placeholder-model"
    assert response.used_fallback_router is True
