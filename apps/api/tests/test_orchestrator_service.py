from app.models.orchestrator import OrchestratorIntent, OrchestratorQueryRequest
from app.services.orchestrator_service import OrchestratorService


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
