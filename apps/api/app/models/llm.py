from typing import Literal

from pydantic import BaseModel, Field


AIProvider = Literal["disabled", "mock", "openai", "ollama"]
AIRoutingMode = Literal["rule_based", "mock_llm", "openai", "ollama", "disabled"]


class AIRoutingMetadata(BaseModel):
    ai_provider: str = Field(alias="aiProvider")
    ai_mode: AIRoutingMode = Field(alias="aiMode")
    model_name: str | None = Field(default=None, alias="modelName")
    model_call_attempted: bool = Field(alias="modelCallAttempted")
    model_call_succeeded: bool = Field(alias="modelCallSucceeded")
    used_fallback_router: bool = Field(alias="usedFallbackRouter")
