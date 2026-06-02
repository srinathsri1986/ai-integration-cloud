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


@dataclass(frozen=True)
class LLMNarrativeResult:
    narrative: str
    model_name: str
    model_call_attempted: bool
    model_call_succeeded: bool
    provider_name: str


@dataclass(frozen=True)
class LLMFlowSuggestionResult:
    suggested_flow: dict
    rationale: str
    model_name: str
    model_call_attempted: bool
    model_call_succeeded: bool
    provider_name: str


@dataclass(frozen=True)
class LLMMappingSuggestionResult:
    suggestions: list[dict]
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

    def generate_narrative(self, context: dict) -> LLMNarrativeResult:
        """Return a concise executive narrative from approved summarized CFO data only."""

    def generate_flow_suggestion(self, context: dict) -> LLMFlowSuggestionResult:
        """Return a draft flow definition using approved connectors and actions only."""

    def generate_mapping_suggestion(self, context: dict) -> LLMMappingSuggestionResult:
        """Return draft field mapping suggestions from approved object metadata only."""


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

    def generate_narrative(self, context: dict) -> LLMNarrativeResult:
        intent = context.get("intent", "UNKNOWN")
        highlights = context.get("highlights", [])
        lead = highlights[0] if highlights else "Approved CFO data was retrieved successfully."
        narrative = (
            f"{intent}: {lead} Finance leadership should review the approved result set, "
            "confirm material variances, and follow up on any operating risks shown in the "
            "dashboard."
        )

        return LLMNarrativeResult(
            narrative=_validate_narrative_text(narrative),
            model_name=self.model_name,
            model_call_attempted=False,
            model_call_succeeded=False,
            provider_name=self.provider_name,
        )

    def generate_flow_suggestion(self, context: dict) -> LLMFlowSuggestionResult:
        prompt = str(context.get("prompt", "")).lower()
        suggested_flow = _template_flow_suggestion(prompt)
        return LLMFlowSuggestionResult(
            suggested_flow=suggested_flow,
            rationale="Mock provider selected approved CFO actions from the governed tool catalog.",
            model_name=self.model_name,
            model_call_attempted=False,
            model_call_succeeded=False,
            provider_name=self.provider_name,
        )

    def generate_mapping_suggestion(self, context: dict) -> LLMMappingSuggestionResult:
        return LLMMappingSuggestionResult(
            suggestions=_template_mapping_suggestions(context),
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

    def generate_narrative(self, context: dict) -> LLMNarrativeResult:
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
                        "Generate a concise CFO executive narrative from only the approved "
                        "summarized JSON provided by the application. Return only JSON with key "
                        "narrative. Keep it under 900 characters. Do not ask for or include "
                        "credentials, raw transactions, SQL, SuiteQL, raw NetSuite queries, or "
                        "tool calls."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, separators=(",", ":")),
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
                "OpenAI narrative generation request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            output_text = _extract_output_text(body)
            parsed = json.loads(output_text)
            narrative = _validated_narrative_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "OpenAI narrative generation returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMNarrativeResult(
            narrative=narrative,
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )

    def generate_flow_suggestion(self, context: dict) -> LLMFlowSuggestionResult:
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
                    "content": _flow_suggestion_system_prompt(),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, separators=(",", ":")),
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
                "OpenAI flow suggestion request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            parsed = json.loads(_extract_output_text(body))
            suggested_flow, rationale = _validated_flow_suggestion_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "OpenAI flow suggestion returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMFlowSuggestionResult(
            suggested_flow=suggested_flow,
            rationale=rationale,
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )

    def generate_mapping_suggestion(self, context: dict) -> LLMMappingSuggestionResult:
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
                    "content": _mapping_suggestion_system_prompt(),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, separators=(",", ":")),
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
                "OpenAI mapping suggestion request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            parsed = json.loads(_extract_output_text(body))
            suggestions = _validated_mapping_suggestion_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "OpenAI mapping suggestion returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMMappingSuggestionResult(
            suggestions=suggestions,
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
            parsed = json.loads(_strip_markdown_json_fence(body["response"]))
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

    def generate_narrative(self, context: dict) -> LLMNarrativeResult:
        prompt = (
            "You are a safe CFO narrative generator. Generate a concise executive narrative "
            "from only the approved summarized JSON below. Return only JSON with key narrative. "
            "Keep it under 900 characters. Do not include credentials, raw transactions, SQL, "
            "SuiteQL, raw NetSuite queries, or tool calls.\n\n"
            f"Approved summarized CFO JSON: {json.dumps(context, separators=(',', ':'))}"
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
                "Ollama narrative generation request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            parsed = json.loads(_strip_markdown_json_fence(body["response"]))
            narrative = _validated_narrative_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "Ollama narrative generation returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMNarrativeResult(
            narrative=narrative,
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )

    def generate_flow_suggestion(self, context: dict) -> LLMFlowSuggestionResult:
        prompt = (
            f"{_flow_suggestion_system_prompt()}\n\n"
            f"Approved flow request context: {json.dumps(context, separators=(',', ':'))}"
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
                "Ollama flow suggestion request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            parsed = json.loads(_strip_markdown_json_fence(body["response"]))
            suggested_flow, rationale = _validated_flow_suggestion_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "Ollama flow suggestion returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMFlowSuggestionResult(
            suggested_flow=suggested_flow,
            rationale=rationale,
            model_name=self.model_name,
            model_call_attempted=True,
            model_call_succeeded=True,
            provider_name=self.provider_name,
        )

    def generate_mapping_suggestion(self, context: dict) -> LLMMappingSuggestionResult:
        prompt = (
            f"{_mapping_suggestion_system_prompt()}\n\n"
            f"Approved mapping request context: {json.dumps(context, separators=(',', ':'))}"
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
                "Ollama mapping suggestion request failed.",
                model_call_attempted=True,
            ) from exc

        try:
            parsed = json.loads(_strip_markdown_json_fence(body["response"]))
            suggestions = _validated_mapping_suggestion_payload(parsed)
        except Exception as exc:
            raise LLMProviderError(
                "Ollama mapping suggestion returned invalid structured output.",
                model_call_attempted=True,
            ) from exc

        return LLMMappingSuggestionResult(
            suggestions=suggestions,
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


def _strip_markdown_json_fence(text: str) -> str:
    normalized = text.strip()

    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()

    return normalized


def _validated_intent_payload(parsed: dict) -> tuple[OrchestratorIntent, float]:
    intent = OrchestratorIntent(parsed["intent"])
    confidence = float(parsed["confidence"])

    if confidence < 0 or confidence > 1:
        raise ValueError("confidence must be between 0 and 1")

    return intent, confidence


def _validated_narrative_payload(parsed: dict) -> str:
    return _validate_narrative_text(parsed["narrative"])


def _validate_narrative_text(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("narrative must be a string")

    normalized = " ".join(text.split())

    if len(normalized) < 20:
        raise ValueError("narrative is too short")

    if len(normalized) > 900:
        raise ValueError("narrative is too long")

    blocked_terms = ["select *", "suiteql", "sql query", "password", "token secret"]
    if any(term in normalized.lower() for term in blocked_terms):
        raise ValueError("narrative included blocked sensitive or raw-query language")

    return normalized


def _flow_suggestion_system_prompt() -> str:
    return (
        "You are a governed integration flow planner. Return only JSON with keys "
        "suggestedFlow and rationale. suggestedFlow must include flowId, name, "
        "description, sourceConnector, targetModule, status, triggerType, and steps. "
        "sourceConnector must be netsuite. status must be draft. triggerType must be "
        "manual or schedule_placeholder. Each step must include id, name, description, "
        "and approvedTool. approvedTool must be one of: cfo.dashboard_summary, "
        "cfo.pl_vs_budget, cfo.yoy_comparison, cfo.subsidiary_drilldown, "
        "cfo.running_projects, cfo.overdue_projects_by_account_manager, "
        "orchestrator.query. Do not include SQL, SuiteQL, credentials, raw NetSuite "
        "queries, arbitrary code, execution commands, publish instructions, or tool calls."
    )


def _validated_flow_suggestion_payload(parsed: dict) -> tuple[dict, str]:
    suggested_flow = parsed["suggestedFlow"]
    rationale = str(parsed["rationale"])

    if not isinstance(suggested_flow, dict):
        raise ValueError("suggestedFlow must be an object")

    if len(rationale) < 10 or len(rationale) > 600:
        raise ValueError("rationale length is outside the allowed range")

    return suggested_flow, rationale


def _mapping_suggestion_system_prompt() -> str:
    return (
        "You are a governed data mapping assistant for an AI-native integration platform. "
        "Return only JSON with key suggestions. suggestions must be an array of objects with "
        "sourceField, targetField, transform, confidence, and rationale. Use only source field "
        "names and target field names provided in the request context. transform must be one of "
        "direct, rename, format_date, lookup_placeholder, constant_placeholder. confidence must "
        "be between 0 and 1. Do not include SQL, SuiteQL, raw queries, credentials, secrets, "
        "arbitrary code, execution commands, save instructions, or publish instructions."
    )


def _validated_mapping_suggestion_payload(parsed: dict) -> list[dict]:
    suggestions = parsed["suggestions"]

    if not isinstance(suggestions, list):
        raise ValueError("suggestions must be an array")

    if len(suggestions) > 12:
        suggestions = suggestions[:12]

    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            raise ValueError("each mapping suggestion must be an object")
        for key in ["sourceField", "targetField", "transform", "confidence", "rationale"]:
            if key not in suggestion:
                raise ValueError(f"mapping suggestion missing {key}")

    return suggestions


def _template_flow_suggestion(prompt: str) -> dict:
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

    if any(term in normalized for term in ["subsidiary", "drilldown", "drill down"]):
        steps.append(
            {
                "id": "load-subsidiary-drilldown",
                "name": "Load subsidiary drilldown",
                "description": "Load approved subsidiary operating performance data.",
                "approvedTool": "cfo.subsidiary_drilldown",
            }
        )

    if "yoy" in normalized or "year over year" in normalized or "year-over-year" in normalized:
        steps.append(
            {
                "id": "compare-yoy",
                "name": "Compare YoY performance",
                "description": "Compare approved current year and prior year metrics.",
                "approvedTool": "cfo.yoy_comparison",
            }
        )

    if any(term in normalized for term in ["narrative", "summary", "ai", "cfo"]):
        steps.append(
            {
                "id": "route-approved-cfo-question",
                "name": "Route approved CFO question",
                "description": "Route a governed CFO question without direct tool execution by the model.",
                "approvedTool": "orchestrator.query",
            }
        )

    deduped_steps = []
    seen_tools = set()
    for step in steps:
        if step["approvedTool"] not in seen_tools:
            seen_tools.add(step["approvedTool"])
            deduped_steps.append(step)

    return {
        "flowId": "ai-drafted-cfo-flow",
        "name": "AI drafted CFO flow",
        "description": (
            "Draft CFO orchestration generated from a natural-language request using approved "
            "NetSuite actions only."
        ),
        "sourceConnector": "netsuite",
        "targetModule": "cfo_dashboard",
        "status": "draft",
        "triggerType": "schedule_placeholder" if "monthly" in normalized or "schedule" in normalized else "manual",
        "steps": deduped_steps[:8],
    }


def _template_mapping_suggestions(context: dict) -> list[dict]:
    source_fields = {field["name"] for field in context.get("sourceObject", {}).get("fields", [])}
    target_fields = {field["name"] for field in context.get("targetObject", {}).get("fields", [])}
    candidates = [
        {
            "sourceField": "customer_name",
            "targetField": "AccountName",
            "transform": "direct",
            "confidence": 0.94,
            "rationale": "Customer names align to the target account reference.",
        },
        {
            "sourceField": "budget_amount",
            "targetField": "Amount",
            "transform": "direct",
            "confidence": 0.91,
            "rationale": "Budget and amount fields share numeric finance meaning.",
        },
        {
            "sourceField": "due_date",
            "targetField": "CloseDate",
            "transform": "format_date",
            "confidence": 0.88,
            "rationale": "Date values need target system date formatting.",
        },
        {
            "sourceField": "account_manager",
            "targetField": "OwnerName",
            "transform": "direct",
            "confidence": 0.84,
            "rationale": "Owner fields represent the responsible business person.",
        },
        {
            "sourceField": "project_id",
            "targetField": "externalId",
            "transform": "rename",
            "confidence": 0.78,
            "rationale": "The project identifier can seed an external reference.",
        },
        {
            "sourceField": "customer",
            "targetField": "displayName",
            "transform": "rename",
            "confidence": 0.86,
            "rationale": "Customer text can become the display name.",
        },
        {
            "sourceField": "invoice_number",
            "targetField": "externalId",
            "transform": "rename",
            "confidence": 0.82,
            "rationale": "Invoice number can be retained as an external identifier.",
        },
    ]

    return [
        suggestion
        for suggestion in candidates
        if suggestion["sourceField"] in source_fields and suggestion["targetField"] in target_fields
    ][:8]


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
