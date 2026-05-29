from dataclasses import dataclass
import json
from typing import Protocol
from urllib import request as urllib_request

from app.models.llm import AIProvider
from app.models.orchestrator import OrchestratorIntent


@dataclass(frozen=True)
class LLMIntentResult:
    confidence: float
    intent: OrchestratorIntent
    model_name: str
    model_call_attempted: bool
    model_call_succeeded: bool
    provider_name: str


class LLMProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        model_call_attempted: bool,
        model_call_succeeded: bool = False,
    ) -> None:
        super().__init__(message)
        self.model_call_attempted = model_call_attempted
        self.model_call_succeeded = model_call_succeeded


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
            model_call_attempted=False,
            model_call_succeeded=False,
            provider_name=self.provider_name,
        )


class OpenAIProvider:
    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        endpoint: str = "https://api.openai.com/v1/responses",
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = endpoint

    def extract_intent(self, question: str) -> LLMIntentResult:
        if not self.api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY is not configured.",
                model_call_attempted=False,
            )

        payload = {
            "model": self.model_name,
            "input": [
                {
                    "role": "system",
                    "content": (
                        "Return only JSON with keys intent and confidence. "
                        "The intent must be one of: CFO_DASHBOARD_SUMMARY, PL_VS_BUDGET, "
                        "YOY_COMPARISON, SUBSIDIARY_DRILLDOWN, RUNNING_PROJECTS, "
                        "OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER, UNKNOWN. "
                        "Do not call tools. Do not generate SQL, SuiteQL, or NetSuite queries."
                    ),
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
            "text": {"format": {"type": "json_object"}},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            self.endpoint,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=10) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise LLMProviderError(
                "OpenAI intent extraction request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            output_text = _extract_output_text(body)
            parsed = json.loads(output_text)
            intent = OrchestratorIntent(parsed["intent"])
            confidence = float(parsed["confidence"])
        except Exception as exc:
            raise LLMProviderError(
                "OpenAI intent extraction returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        if confidence < 0 or confidence > 1:
            raise LLMProviderError(
                "OpenAI intent extraction confidence was outside the allowed range.",
                model_call_attempted=True,
            )

        return LLMIntentResult(
            confidence=confidence,
            intent=intent,
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )


class OllamaProvider:
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model_name: str,
        timeout_seconds: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def extract_intent(self, question: str) -> LLMIntentResult:
        prompt = (
            "You are a safe CFO intent classifier. Return only JSON with keys intent and "
            "confidence. The intent must be one of: CFO_DASHBOARD_SUMMARY, PL_VS_BUDGET, "
            "YOY_COMPARISON, SUBSIDIARY_DRILLDOWN, RUNNING_PROJECTS, "
            "OVERDUE_PROJECTS_BY_ACCOUNT_MANAGER, UNKNOWN. Do not call tools. Do not generate "
            "SQL, SuiteQL, raw NetSuite queries, credentials, or secrets.\n\n"
            f"Question: {question}"
        )
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise LLMProviderError(
                "Ollama intent extraction request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            parsed = json.loads(body["response"])
            intent, confidence = _validated_intent_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "Ollama intent extraction returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMIntentResult(
            confidence=confidence,
            intent=intent,
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )


def _extract_output_text(body: dict) -> str:
    if isinstance(body.get("output_text"), str):
        return body["output_text"]

    for item in body.get("output", []):
        for content in item.get("content", []):
            if isinstance(content.get("text"), str):
                return content["text"]

    raise ValueError("No structured output text found.")


def _validated_intent_payload(parsed: dict) -> tuple[OrchestratorIntent, float]:
    intent = OrchestratorIntent(parsed["intent"])
    confidence = float(parsed["confidence"])

    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    return intent, confidence


def make_llm_provider(
    provider: AIProvider,
    model_name: str,
    openai_api_key: str | None = None,
    ollama_base_url: str = "http://localhost:11434",
    ollama_timeout_seconds: int = 20,
) -> LLMProvider | None:
    if provider == "mock":
        return MockLLMProvider(model_name=model_name)

    if provider == "openai":
        return OpenAIProvider(api_key=openai_api_key, model_name=model_name)

    if provider == "ollama":
        return OllamaProvider(
            base_url=ollama_base_url,
            model_name=model_name,
            timeout_seconds=ollama_timeout_seconds,
        )

    return None
