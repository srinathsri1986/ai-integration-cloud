from typing import Literal

from pydantic import BaseModel, Field


AIProviderMode = Literal["disabled", "mock", "openai_placeholder", "anthropic_placeholder"]
AIRoutingMode = Literal["rule_based", "mock_llm", "disabled"]


class AIRoutingMetadata(BaseModel):
    ai_provider: str = Field(alias="aiProvider")
    ai_mode: AIRoutingMode = Field(alias="aiMode")
    model_name: str | None = Field(default=None, alias="modelName")
    used_fallback_router: bool = Field(alias="usedFallbackRouter")
