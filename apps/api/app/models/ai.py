"""Models for the universal Ask AI endpoint (POST /api/v1/ai/ask)."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

_BLOCKED_TERMS = ["select *", "suiteql", "sql query", "raw query", "password", "secret"]

# Intent values returned by the Ask AI service
ASK_AI_INTENT_CREATE_FLOW = "CREATE_FLOW"
ASK_AI_INTENT_SUGGEST_MAPPING = "SUGGEST_MAPPING"
ASK_AI_INTENT_EXPLAIN_ERROR = "EXPLAIN_ERROR"
ASK_AI_INTENT_GENERAL = "GENERAL"

# Action type values — tell the frontend what to do with the response
ASK_AI_ACTION_SUGGEST_FLOW = "SUGGEST_FLOW"
ASK_AI_ACTION_OPEN_MAPPING = "OPEN_MAPPING"
ASK_AI_ACTION_OPEN_ERROR_DEBUGGER = "OPEN_ERROR_DEBUGGER"
ASK_AI_ACTION_INFO = "INFO"


class AskAIRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    page_context: str | None = Field(default=None, alias="pageContext")

    model_config = {"populate_by_name": True}

    @field_validator("question")
    @classmethod
    def reject_raw_query_language(cls, value: str) -> str:
        normalized = value.lower()
        if any(term in normalized for term in _BLOCKED_TERMS):
            raise ValueError(
                "Questions cannot contain raw query language, credentials, or secrets."
            )
        return value


class AskAIAction(BaseModel):
    """Frontend action to take after receiving the AI answer."""
    type: str  # ASK_AI_ACTION_* constant
    navigate_to: str | None = Field(default=None, alias="navigateTo")
    # Structured payload — e.g. FlowSuggestionResponse serialised to dict for CREATE_FLOW
    payload: dict | None = None

    model_config = {"populate_by_name": True}


class AskAIResponse(BaseModel):
    question: str
    intent: str                         # ASK_AI_INTENT_* constant
    answer: str                         # Human-readable explanation shown in the panel
    action: AskAIAction | None = None   # Optional follow-up action for the frontend
    provider: str                       # "mock" | "ollama" | "openai" | "template"
    model: str | None = None
    think_used: bool = Field(default=False, alias="thinkUsed")

    model_config = {"populate_by_name": True}
