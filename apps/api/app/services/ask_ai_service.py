"""Ask AI service — routes natural language questions to the right sub-service.

Architecture:
  1. Fast keyword-based intent detection (no LLM call, < 1ms) covers common patterns.
  2. For CREATE_FLOW: delegates to flow_suggestion_service (Qwen3, think=True).
  3. For SUGGEST_MAPPING / EXPLAIN_ERROR: returns navigation action + template answer.
  4. For GENERAL: returns a curated platform answer (template in mock mode, Qwen3 in ollama).

The AI drafts everything; humans approve before production execution.
"""
from __future__ import annotations

import re

from app.models.ai import (
    ASK_AI_ACTION_INFO,
    ASK_AI_ACTION_OPEN_ERROR_DEBUGGER,
    ASK_AI_ACTION_OPEN_MAPPING,
    ASK_AI_ACTION_SUGGEST_FLOW,
    ASK_AI_INTENT_CREATE_FLOW,
    ASK_AI_INTENT_EXPLAIN_ERROR,
    ASK_AI_INTENT_GENERAL,
    ASK_AI_INTENT_SUGGEST_MAPPING,
    AskAIAction,
    AskAIRequest,
    AskAIResponse,
)
from app.models.flows import FlowSuggestionRequest
from app.services.flow_suggestion_service import FlowSuggestionService

# ── Intent detection ──────────────────────────────────────────────────────────

_FLOW_PATTERNS = re.compile(
    r"\b(create|build|generate|make|set up|setup|schedule|design|add)\b.{0,40}"
    r"\b(flow|workflow|integration|sync|trigger|connector|pipeline|process)\b",
    re.IGNORECASE,
)
_FLOW_KEYWORDS = frozenset([
    "sync ", "workflow", "integrate", "trigger ", "schedule ", "every hour",
    "every day", "every minute", "every 15", "webhook trigger", "flow to",
    "integration flow", "send notification when",
])

_MAPPING_PATTERNS = re.compile(
    r"\b(map|mapping|field|schema|source field|target field|suggest mapping)\b",
    re.IGNORECASE,
)

_ERROR_PATTERNS = re.compile(
    r"\b(error|fail|failed|failure|debug|diagnose|fix|broken|why did|root cause|"
    r"400|401|403|404|500|502|503|entityid|missing field|missing error|"
    r"run RUN-|run id|failed run|failed workflow)\b",
    re.IGNORECASE,
)


def _detect_intent(question: str) -> str:
    q = question.lower()

    # Error intent has priority — a question with "fail/error/debug/fix" is about
    # troubleshooting even if it also mentions "workflow" or "sync".
    if _ERROR_PATTERNS.search(question):
        return ASK_AI_INTENT_EXPLAIN_ERROR

    if _FLOW_PATTERNS.search(question) or any(kw in q for kw in _FLOW_KEYWORDS):
        return ASK_AI_INTENT_CREATE_FLOW

    if _MAPPING_PATTERNS.search(question):
        return ASK_AI_INTENT_SUGGEST_MAPPING

    return ASK_AI_INTENT_GENERAL


# ── Template answers for non-flow intents ────────────────────────────────────

_GENERAL_ANSWERS: dict[str, str] = {
    "connector": (
        "This platform supports: Salesforce, NetSuite, Oracle Fusion, ServiceNow, SAP, "
        "HubSpot, Workday, PostgreSQL, REST API, SOAP API, Webhook, and SFTP. "
        "Open the Connector Marketplace to connect and configure each system."
    ),
    "approval": (
        "Every AI-generated workflow, mapping, and transformation goes through the Approval Center "
        "before it can be published to production. Reviewers can approve, reject, or request changes. "
        "High-risk changes (new OAuth scopes, production publishes) require explicit sign-off."
    ),
    "mock": (
        "Mock mode runs the platform with simulated connector responses — no real API calls are made. "
        "Set AI_PROVIDER=ollama and start Ollama locally to switch to live Qwen3 AI suggestions. "
        "Set NETSUITE_MODE=sandbox with your NetSuite credentials for live connector data."
    ),
    "version": (
        "Every workflow, mapping, connector, and transformation is versioned automatically. "
        "You can compare versions, roll back to any previous state, and see who made each change "
        "in the Version History and Audit Log screens."
    ),
}

_FALLBACK_GENERAL = (
    "This is an AI-native iPaaS platform. You can describe integrations in plain English and "
    "the AI will generate workflows, map fields, and debug errors — all subject to human approval "
    "before production execution. Try: 'Create a flow to sync NetSuite to Salesforce every hour'."
)

_MAPPING_ANSWER = (
    "Open the AI Field Mapping studio to get AI-suggested field mappings with confidence scores. "
    "The model will match source and target fields semantically — you approve, edit, or regenerate "
    "each suggestion before saving."
)

_ERROR_ANSWER = (
    "Go to the AI Error Debugger to diagnose failed runs. The AI analyses the failed step, "
    "HTTP response, payload, and logs to identify the root cause and recommend a fix — "
    "which requires human approval before being applied to production."
)


def _general_answer(question: str) -> str:
    q = question.lower()
    for keyword, answer in _GENERAL_ANSWERS.items():
        # Allow partial matches: "approval center" matches key "approval"
        if keyword in q:
            return answer
    return _FALLBACK_GENERAL


# ── Mapping context extraction ────────────────────────────────────────────────

# (system_id, object_keyword) → catalog object ID
_OBJECT_MAP: dict[str, dict[str, str]] = {
    "netsuite": {
        "customer":       "netsuite-customer",
        "contact":        "netsuite-contact",
        "opportunity":    "netsuite-opportunity",
        "sales order":    "netsuite-sales-order",
        "order":          "netsuite-sales-order",
        "invoice":        "netsuite-invoice",
        "vendor bill":    "netsuite-vendor-bill",
        "vendor":         "netsuite-vendor-bill",
        "purchase order": "netsuite-purchase-order",
        "journal":        "netsuite-journal-entry",
        "employee":       "netsuite-employee",
        "item":           "netsuite-item",
        "product":        "netsuite-item",
        "expense":        "netsuite-expense-report",
        "subsidiary":     "netsuite-subsidiary",
        "project":        "netsuite-project",
    },
    "salesforce": {
        "account":        "salesforce-account",
        "contact":        "salesforce-contact",
        "opportunity":    "salesforce-opportunity",
        "project":        "salesforce-project-c",
        # Cross-system aliases — customer/vendor both land on Account in Salesforce
        "customer":       "salesforce-account",
        "vendor":         "salesforce-account",
    },
    "sap": {
        "vendor":         "sap-vendor",
        "journal line":   "sap-journal-line",
        "journal":        "sap-journal-entry",
        "cost center":    "sap-cost-center",
    },
}

_DEFAULT_OBJECT: dict[str, str] = {
    "netsuite":   "netsuite-customer",
    "salesforce": "salesforce-account",
    "sap":        "sap-vendor",
}

_CONNECTOR_LABELS: dict[str, str] = {
    "netsuite":   "NetSuite",
    "salesforce": "Salesforce",
    "sap":        "SAP",
    "oracle":     "Oracle",
    "servicenow": "ServiceNow",
    "hubspot":    "HubSpot",
}

_OBJECT_LABELS: dict[str, str] = {
    "netsuite-customer":        "Customer",
    "netsuite-contact":         "Contact",
    "netsuite-opportunity":     "Opportunity",
    "netsuite-sales-order":     "Sales Order",
    "netsuite-invoice":         "Invoice",
    "netsuite-vendor-bill":     "Vendor Bill",
    "netsuite-purchase-order":  "Purchase Order",
    "netsuite-journal-entry":   "Journal Entry",
    "netsuite-employee":        "Employee",
    "netsuite-item":            "Item",
    "netsuite-expense-report":  "Expense Report",
    "netsuite-subsidiary":      "Subsidiary",
    "netsuite-project":         "Project",
    "salesforce-account":       "Account",
    "salesforce-contact":       "Contact",
    "salesforce-opportunity":   "Opportunity",
    "salesforce-project-c":     "Project",
    "sap-vendor":               "Vendor",
    "sap-journal-entry":        "Journal Entry",
    "sap-journal-line":         "Journal Line",
    "sap-cost-center":          "Cost Center",
}


def _best_object_id(system_id: str, text: str) -> str:
    """Return the best-matching catalog object ID for a system given a text snippet.

    Matches longest keyword first so 'sales order' beats 'order'.
    """
    obj_map = _OBJECT_MAP.get(system_id, {})
    for keyword in sorted(obj_map, key=len, reverse=True):
        if keyword in text.lower():
            return obj_map[keyword]
    return _DEFAULT_OBJECT.get(system_id, f"{system_id}-record")


def _parse_mapping_context(question: str) -> dict:
    """Extract source/target system + object IDs from a mapping question.

    Returns a dict with sourceSystemId, sourceObjectId, targetSystemId,
    targetObjectId, and a ready-made mappingPrompt.
    """
    from app.services.flow_suggestion_service import _detect_connector_pair

    src_connector, tgt_connector = _detect_connector_pair(question)

    # connector IDs from flow detection are full slugs (e.g. "rest-api").
    # systemId in the mapping catalog is always the first segment.
    src_system = src_connector.split("-")[0] if "-" in src_connector else src_connector
    tgt_system = tgt_connector.split("-")[0] if "-" in tgt_connector else tgt_connector

    # Split the sentence at the target connector's position so that object keywords
    # on the target side (e.g. "opportunity" in "to Salesforce opportunity") don't
    # bleed into the source object detection and vice versa.
    q_lower = question.lower()
    tgt_pos = q_lower.find(tgt_system) if tgt_system != "target-system" else -1
    if tgt_pos > 0:
        src_text = q_lower[:tgt_pos]
        tgt_text = q_lower[tgt_pos:]
    else:
        src_text = q_lower
        tgt_text = q_lower

    src_obj = _best_object_id(src_system, src_text)
    tgt_obj = _best_object_id(tgt_system, tgt_text)

    src_label = _CONNECTOR_LABELS.get(src_system, src_system.title())
    tgt_label = _CONNECTOR_LABELS.get(tgt_system, tgt_system.title())
    src_obj_label = _OBJECT_LABELS.get(src_obj, src_obj.replace("-", " ").title())
    tgt_obj_label = _OBJECT_LABELS.get(tgt_obj, tgt_obj.replace("-", " ").title())

    mapping_prompt = (
        f"Map {src_label} {src_obj_label} fields to {tgt_label} {tgt_obj_label}. "
        f"Suggest field-level transformations with confidence scores."
    )

    return {
        "sourceSystemId":  src_system,
        "sourceObjectId":  src_obj,
        "targetSystemId":  tgt_system,
        "targetObjectId":  tgt_obj,
        "mappingPrompt":   mapping_prompt,
    }


# ── Service ───────────────────────────────────────────────────────────────────

class AskAIService:
    """Routes Ask AI requests to the appropriate sub-service and returns a structured response."""

    def __init__(self, flow_suggestion_svc: FlowSuggestionService | None = None) -> None:
        # Lazy import to avoid circular dependency; override in tests
        if flow_suggestion_svc is None:
            from app.services.flow_suggestion_service import flow_suggestion_service
            self._flow_svc = flow_suggestion_service
        else:
            self._flow_svc = flow_suggestion_svc

    def ask(self, request: AskAIRequest) -> AskAIResponse:
        intent = _detect_intent(request.question)

        if intent == ASK_AI_INTENT_CREATE_FLOW:
            return self._handle_create_flow(request)

        if intent == ASK_AI_INTENT_SUGGEST_MAPPING:
            mapping_ctx = _parse_mapping_context(request.question)
            src_label = _CONNECTOR_LABELS.get(mapping_ctx["sourceSystemId"],
                                               mapping_ctx["sourceSystemId"].title())
            tgt_label = _CONNECTOR_LABELS.get(mapping_ctx["targetSystemId"],
                                               mapping_ctx["targetSystemId"].title())
            src_obj_label = _OBJECT_LABELS.get(mapping_ctx["sourceObjectId"],
                                                mapping_ctx["sourceObjectId"].replace("-", " ").title())
            tgt_obj_label = _OBJECT_LABELS.get(mapping_ctx["targetObjectId"],
                                                mapping_ctx["targetObjectId"].replace("-", " ").title())
            answer = (
                f"Opening the Data Mapping Studio pre-filled for "
                f"{src_label} {src_obj_label} → {tgt_label} {tgt_obj_label}. "
                "AI-suggested field mappings with confidence scores are ready to review."
            )
            return AskAIResponse(
                question=request.question,
                intent=intent,
                answer=answer,
                action=AskAIAction(
                    type=ASK_AI_ACTION_OPEN_MAPPING,
                    navigateTo="/mapping",
                    payload=mapping_ctx,
                ),
                provider="template",
                model=None,
                thinkUsed=False,
            )

        if intent == ASK_AI_INTENT_EXPLAIN_ERROR:
            return AskAIResponse(
                question=request.question,
                intent=intent,
                answer=_ERROR_ANSWER,
                action=AskAIAction(
                    type=ASK_AI_ACTION_OPEN_ERROR_DEBUGGER,
                    navigateTo="/flows/runs",
                ),
                provider="template",
                model=None,
                thinkUsed=False,
            )

        # GENERAL
        return AskAIResponse(
            question=request.question,
            intent=ASK_AI_INTENT_GENERAL,
            answer=_general_answer(request.question),
            action=AskAIAction(type=ASK_AI_ACTION_INFO),
            provider="template",
            model=None,
            thinkUsed=False,
        )

    def _handle_create_flow(self, request: AskAIRequest) -> AskAIResponse:
        flow_request = FlowSuggestionRequest(prompt=request.question)
        result = self._flow_svc.suggest(flow_request)

        answer = (
            f"I've drafted an integration flow: \"{result.suggested_flow.name}\". "
            f"{result.rationale} "
            "Review the suggested steps, check the mapping confidence, and run a sandbox test "
            "before publishing to production."
        )

        return AskAIResponse(
            question=request.question,
            intent=ASK_AI_INTENT_CREATE_FLOW,
            answer=answer,
            action=AskAIAction(
                type=ASK_AI_ACTION_SUGGEST_FLOW,
                navigateTo="/flows/builder",
                payload=result.model_dump(by_alias=True),
            ),
            provider=result.suggestion_provider,
            model=result.suggestion_model,
            thinkUsed=False,
        )


ask_ai_service = AskAIService()
