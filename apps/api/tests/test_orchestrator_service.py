import json

from app.models.orchestrator import OrchestratorIntent, OrchestratorQueryRequest
from app.services.llm_provider import LLMIntentResult, OllamaProvider, OpenAIProvider
from app.services.orchestrator_service import OrchestratorService


class FakeHTTPResponse:
    def __init__(self, body: dict) -> None:
        self.body = body

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


class FailingLLMProvider:
    provider_name = "openai"
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
    service = OrchestratorService(ai_provider="disabled")

    response = service.query(
        OrchestratorQueryRequest(question="Can you run select * from transaction?")
    )

    assert response.detected_intent == OrchestratorIntent.UNKNOWN
    assert response.tools_used == []
    assert response.ai_mode == "rule_based"
    assert response.used_fallback_router is False


def test_default_intent_extraction_uses_rule_based_router() -> None:
    service = OrchestratorService(ai_provider="disabled")

    match = service.extract_intent("Compare revenue year over year")

    assert match.intent == OrchestratorIntent.YOY_COMPARISON
    assert match.ai_provider == "none"
    assert match.ai_mode == "rule_based"
    assert match.model_name is None
    assert match.used_fallback_router is False


def test_mock_llm_intent_routing() -> None:
    service = OrchestratorService(ai_provider="mock", model_name="mock-cfo-intent-v0")

    response = service.query(
        OrchestratorQueryRequest(question="Which projects are overdue by account manager?")
    )

    assert response.detected_intent == OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER
    assert response.tools_used == ["cfo.overdue_projects_by_account_manager"]
    assert response.ai_provider == "mock"
    assert response.ai_mode == "mock_llm"
    assert response.model_name == "mock-cfo-intent-v0"
    assert response.model_call_attempted is False
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is False


def test_provider_failure_falls_back_to_rule_based_router() -> None:
    service = OrchestratorService(
        ai_provider="openai",
        model_name="failing-mock",
        llm_provider=FailingLLMProvider(),
    )

    response = service.query(OrchestratorQueryRequest(question="Show me P/L vs budget for Q1"))

    assert response.detected_intent == OrchestratorIntent.PL_VS_BUDGET
    assert response.tools_used == ["cfo.pl_vs_budget"]
    assert response.ai_provider == "openai"
    assert response.ai_mode == "openai"
    assert response.model_name == "failing-mock"
    assert response.model_call_attempted is False
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True


def test_openai_without_key_uses_rule_based_fallback_without_external_call() -> None:
    service = OrchestratorService(
        ai_provider="openai",
        model_name="placeholder-model",
        openai_api_key="",
    )

    response = service.query(OrchestratorQueryRequest(question="Show EMEA subsidiary drilldown"))

    assert response.detected_intent == OrchestratorIntent.SUBSIDIARY_DRILLDOWN
    assert response.tools_used == ["cfo.subsidiary_drilldown"]
    assert response.ai_provider == "openai"
    assert response.ai_mode == "openai"
    assert response.model_name == "placeholder-model"
    assert response.model_call_attempted is False
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True


def test_openai_provider_validates_mocked_structured_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "output_text": json.dumps(
                    {"intent": "YOY_COMPARISON", "confidence": 0.82}
                )
            }
        )

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OpenAIProvider(api_key="test-key", model_name="gpt-test")
    service = OrchestratorService(
        ai_provider="openai",
        model_name="gpt-test",
        llm_provider=provider,
        openai_api_key="test-key",
    )

    response = service.query(OrchestratorQueryRequest(question="Compare revenue year over year"))

    assert response.detected_intent == OrchestratorIntent.YOY_COMPARISON
    assert response.tools_used == ["cfo.yoy_comparison"]
    assert response.ai_provider == "openai"
    assert response.ai_mode == "openai"
    assert response.model_name == "gpt-test"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is True
    assert response.used_fallback_router is False


def test_openai_invalid_output_falls_back_to_rule_based_router(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "output_text": json.dumps(
                    {"intent": "RUN_FREEFORM_SQL", "confidence": 0.95}
                )
            }
        )

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OpenAIProvider(api_key="test-key", model_name="gpt-test")
    service = OrchestratorService(
        ai_provider="openai",
        model_name="gpt-test",
        llm_provider=provider,
        openai_api_key="test-key",
    )

    response = service.query(OrchestratorQueryRequest(question="Show me P/L vs budget for Q1"))

    assert response.detected_intent == OrchestratorIntent.PL_VS_BUDGET
    assert response.tools_used == ["cfo.pl_vs_budget"]
    assert response.ai_provider == "openai"
    assert response.ai_mode == "openai"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True


def test_openai_request_failure_falls_back_to_rule_based_router(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise TimeoutError("offline")

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OpenAIProvider(api_key="test-key", model_name="gpt-test")
    service = OrchestratorService(
        ai_provider="openai",
        model_name="gpt-test",
        llm_provider=provider,
        openai_api_key="test-key",
    )

    response = service.query(OrchestratorQueryRequest(question="Show running project status"))

    assert response.detected_intent == OrchestratorIntent.RUNNING_PROJECTS
    assert response.tools_used == ["cfo.running_projects"]
    assert response.ai_provider == "openai"
    assert response.ai_mode == "openai"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True


def test_ollama_provider_validates_raw_json_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "response": json.dumps(
                    {"intent": "PL_VS_BUDGET", "confidence": 0.95}
                )
            }
        )

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model_name="qwen3:30b",
        timeout_seconds=20,
    )
    service = OrchestratorService(
        ai_provider="ollama",
        model_name="qwen3:30b",
        llm_provider=provider,
    )

    response = service.query(OrchestratorQueryRequest(question="Show me P/L vs budget for Q1"))

    assert response.detected_intent == OrchestratorIntent.PL_VS_BUDGET
    assert response.tools_used == ["cfo.pl_vs_budget"]
    assert response.ai_provider == "ollama"
    assert response.ai_mode == "ollama"
    assert response.model_name == "qwen3:30b"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is True
    assert response.used_fallback_router is False


def test_ollama_provider_validates_fenced_json_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "response": (
                    "```json\n"
                    "{\n"
                    '  "intent": "PL_VS_BUDGET",\n'
                    '  "confidence": 0.95\n'
                    "}\n"
                    "```"
                )
            }
        )

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model_name="qwen2.5-coder:7b",
        timeout_seconds=20,
    )
    service = OrchestratorService(
        ai_provider="ollama",
        model_name="qwen2.5-coder:7b",
        llm_provider=provider,
    )

    response = service.query(OrchestratorQueryRequest(question="Show me P/L vs budget for Q1"))

    assert response.detected_intent == OrchestratorIntent.PL_VS_BUDGET
    assert response.tools_used == ["cfo.pl_vs_budget"]
    assert response.ai_provider == "ollama"
    assert response.ai_mode == "ollama"
    assert response.model_name == "qwen2.5-coder:7b"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is True
    assert response.used_fallback_router is False


def test_ollama_invalid_json_falls_back_to_rule_based_router(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse({"response": "not-json"})

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model_name="qwen3:30b",
        timeout_seconds=20,
    )
    service = OrchestratorService(
        ai_provider="ollama",
        model_name="qwen3:30b",
        llm_provider=provider,
    )

    response = service.query(OrchestratorQueryRequest(question="Show EMEA subsidiary drilldown"))

    assert response.detected_intent == OrchestratorIntent.SUBSIDIARY_DRILLDOWN
    assert response.tools_used == ["cfo.subsidiary_drilldown"]
    assert response.ai_provider == "ollama"
    assert response.ai_mode == "ollama"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True


def test_ollama_unsupported_intent_falls_back_to_rule_based_router(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "response": json.dumps(
                    {"intent": "RAW_SUITEQL", "confidence": 0.99}
                )
            }
        )

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model_name="qwen3:30b",
        timeout_seconds=20,
    )
    service = OrchestratorService(
        ai_provider="ollama",
        model_name="qwen3:30b",
        llm_provider=provider,
    )

    response = service.query(OrchestratorQueryRequest(question="Compare revenue year over year"))

    assert response.detected_intent == OrchestratorIntent.YOY_COMPARISON
    assert response.tools_used == ["cfo.yoy_comparison"]
    assert response.ai_provider == "ollama"
    assert response.ai_mode == "ollama"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True


def test_ollama_timeout_falls_back_to_rule_based_router(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise TimeoutError("ollama offline")

    monkeypatch.setattr("app.services.llm_provider.urllib_request.urlopen", fake_urlopen)
    provider = OllamaProvider(
        base_url="http://localhost:11434",
        model_name="qwen3:30b",
        timeout_seconds=20,
    )
    service = OrchestratorService(
        ai_provider="ollama",
        model_name="qwen3:30b",
        llm_provider=provider,
    )

    response = service.query(
        OrchestratorQueryRequest(question="Which projects are overdue by account manager?")
    )

    assert response.detected_intent == OrchestratorIntent.OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER
    assert response.tools_used == ["cfo.overdue_projects_by_account_manager"]
    assert response.ai_provider == "ollama"
    assert response.ai_mode == "ollama"
    assert response.model_call_attempted is True
    assert response.model_call_succeeded is False
    assert response.used_fallback_router is True
