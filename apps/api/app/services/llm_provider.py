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
        think: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        # think=True enables Qwen3 chain-of-thought reasoning (slower, more accurate).
        # Use for deep tasks like mapping suggestion and flow generation.
        # Use think=False for fast classification tasks like intent extraction.
        self.think = think

    def _post(self, payload: dict) -> dict:
        """POST to Ollama /api/generate.

        If think=True and the model returns HTTP 400 (model does not support thinking),
        automatically retries with think=False so non-Qwen3 models work transparently.
        """
        import urllib.error as urllib_error

        def _do_post(p: dict) -> dict:
            data = json.dumps(p).encode("utf-8")
            req = urllib_request.Request(
                f"{self.base_url}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))

        try:
            return _do_post(payload)
        except urllib_error.HTTPError as exc:
            if exc.code == 400 and payload.get("think"):
                # Model doesn't support think mode (e.g. qwen2.5-coder, llama3).
                # Retry without it — qwen3:14b will re-enable it once pulled.
                return _do_post({**payload, "think": False})
            raise

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
            "think": self.think,
        }
        try:
            body = self._post(payload)
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
            "think": self.think,
        }
        try:
            body = self._post(payload)
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
            "think": self.think,
        }
        try:
            body = self._post(payload)
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
            "think": self.think,
        }
        try:
            body = self._post(payload)
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
        "You are a governed iPaaS integration flow planner for an enterprise middleware platform. "
        "Return ONLY a JSON object with two keys: suggestedFlow and rationale.\n\n"
        "suggestedFlow must include: flowId (lowercase slug matching ^[a-z0-9-]+$), name, description "
        "(10-500 chars), sourceConnector, targetModule, targetConnector, status (always 'draft'), "
        "triggerType ('manual', 'schedule', or 'webhook'), triggerCron (cron string when schedule, "
        "null otherwise), and steps (array, 1-8 items).\n\n"
        "Each step must include: id, name, description, and approvedTool. "
        "approvedTool must be exactly one of these approved values:\n"
        "  Generic integration: connector.schedule_trigger, connector.webhook_trigger, "
        "connector.fetch_records, connector.search_records, connector.upsert_record, "
        "connector.create_record, connector.update_record, connector.transform_payload, "
        "connector.send_notification, connector.audit_log, connector.retry_handler\n"
        "  CFO/finance: cfo.dashboard_summary, cfo.pl_vs_budget, cfo.yoy_comparison, "
        "cfo.subsidiary_drilldown, cfo.running_projects, cfo.overdue_projects_by_account_manager, "
        "orchestrator.query\n\n"
        "Typical integration step order: [schedule_trigger or webhook_trigger] → fetch_records → "
        "transform_payload → search_records → upsert_record → audit_log.\n\n"
        "CRITICAL format rules:\n"
        "- flowId MUST use hyphens only, NO underscores. Example: netsuite-to-salesforce-customers\n"
        "- triggerCron MUST be standard 5-field cron (minute hour dom month dow). "
        "Hourly = '0 * * * *', daily = '0 0 * * *', every 15 min = '*/15 * * * *'. "
        "Do NOT use 6-field Quartz cron format (no seconds field, no ? character).\n"
        "- Each step id MUST be a string slug, not a number. Example: 'fetch-source', 'transform', 'upsert-target'.\n\n"
        "rationale must be 10-600 chars explaining the integration design in business language.\n\n"
        "Do not include SQL, SuiteQL, raw queries, credentials, secrets, arbitrary code, "
        "execution commands, publish instructions, or direct tool calls."
    )


def _sanitise_flow_suggestion(flow: dict) -> dict:
    """Normalise common LLM output quirks before Pydantic validation."""
    # flowId: underscores → hyphens; strip anything not in [a-z0-9-]
    if "flowId" in flow and isinstance(flow["flowId"], str):
        fid = flow["flowId"].lower().replace("_", "-").replace(" ", "-")
        fid = "".join(c for c in fid if c.isalnum() or c == "-")
        flow["flowId"] = fid or "ai-drafted-flow"

    # triggerCron: some models emit 6-field Quartz cron (with a leading seconds field
    # and/or a trailing ? day-of-week wildcard). Normalise to standard 5-field POSIX cron.
    if "triggerCron" in flow and isinstance(flow["triggerCron"], str):
        parts = flow["triggerCron"].split()
        if len(parts) == 6:
            # Quartz: seconds minutes hours dom month dow  → drop leading seconds
            parts = parts[1:]
        # Replace Quartz ? wildcard (unsupported by croniter) with *
        parts = ["*" if p == "?" else p for p in parts]
        flow["triggerCron"] = " ".join(parts)

    # steps[*].id: LLM sometimes emits integers (1, 2, 3) instead of string slugs
    if "steps" in flow and isinstance(flow["steps"], list):
        for step in flow["steps"]:
            if isinstance(step, dict) and "id" in step and not isinstance(step["id"], str):
                step["id"] = str(step["id"])

    return flow


def _validated_flow_suggestion_payload(parsed: dict) -> tuple[dict, str]:
    suggested_flow = parsed["suggestedFlow"]
    rationale = str(parsed["rationale"])

    if not isinstance(suggested_flow, dict):
        raise ValueError("suggestedFlow must be an object")

    # Normalise LLM output quirks before Pydantic validates
    suggested_flow = _sanitise_flow_suggestion(suggested_flow)

    if len(rationale) < 10 or len(rationale) > 600:
        raise ValueError("rationale length is outside the allowed range")

    return suggested_flow, rationale


def _mapping_suggestion_system_prompt() -> str:
    return (
        "You are a governed data mapping assistant for an AI-native enterprise integration platform. "
        "Return only JSON with key suggestions. suggestions must be an array of objects, each with "
        "sourceField, targetField, transform, confidence, and rationale.\n\n"
        "Rules:\n"
        "- Use ONLY field names that appear in the sourceObject.fields and targetObject.fields arrays "
        "provided in the context. Never invent field names.\n"
        "- Use field type and sample values to determine the best transform. "
        "If source type is 'date' and target type is 'date', prefer format_date. "
        "If names are semantically similar but differ (e.g. entityId vs External_Id__c), use rename. "
        "If types and names match closely, use direct.\n"
        "- Confidence must be 0.0–1.0 reflecting genuine semantic match quality: "
        "0.9+ for exact semantic matches, 0.7–0.89 for strong matches, below 0.7 for uncertain.\n"
        "- transform must be one of: direct, rename, format_date, lookup_placeholder, constant_placeholder.\n"
        "- Rationale must be a clear business-language explanation (10–240 chars) of why the fields match.\n"
        "- Do not include SQL, SuiteQL, raw queries, credentials, secrets, arbitrary code, "
        "execution commands, save instructions, or publish instructions.\n"
        "- Humans must approve every suggestion before it is applied."
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
            "targetField": "Name",
            "transform": "rename",
            "confidence": 0.8,
            "rationale": "Project identifier can seed a reviewed opportunity name.",
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
    ollama_think: bool = False,
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
            think=ollama_think,
        )

    return None
