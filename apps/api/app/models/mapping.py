from typing import Literal

from pydantic import BaseModel, Field, field_validator


MappingFieldType = Literal["string", "number", "date", "boolean"]
MappingTransform = Literal[
    "direct",
    "rename",
    "format_date",
    "lookup_placeholder",
    "constant_placeholder",
]


class MappingField(BaseModel):
    name: str
    description: str
    type: MappingFieldType
    required: bool = False
    sample: str | int | float | bool | None = None


class MappingObject(BaseModel):
    id: str
    display_name: str = Field(alias="displayName")
    system_id: str = Field(alias="systemId")
    fields: list[MappingField]


class MappingSuggestionRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=1000)
    source_object_id: str = Field(alias="sourceObjectId", min_length=3, max_length=80)
    target_object_id: str = Field(alias="targetObjectId", min_length=3, max_length=80)

    @field_validator("prompt")
    @classmethod
    def reject_raw_query_language(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["select *", "suiteql", "sql query", "raw query", "password", "secret"]
        if any(term in normalized for term in blocked):
            raise ValueError("Mapping prompts cannot request raw queries, credentials, or secrets.")

        return value


class MappingSuggestionItem(BaseModel):
    source_field: str = Field(alias="sourceField")
    target_field: str = Field(alias="targetField")
    transform: MappingTransform
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=10, max_length=240)

    @field_validator("rationale")
    @classmethod
    def reject_sensitive_rationale(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["select *", "suiteql", "sql query", "raw query", "password", "secret"]
        if any(term in normalized for term in blocked):
            raise ValueError("Mapping rationale cannot include raw query or secret language.")

        return value


class MappingSuggestionResponse(BaseModel):
    prompt: str
    source_object_id: str = Field(alias="sourceObjectId")
    target_object_id: str = Field(alias="targetObjectId")
    suggestions: list[MappingSuggestionItem]
    suggestion_provider: str = Field(alias="suggestionProvider")
    suggestion_model: str | None = Field(default=None, alias="suggestionModel")
    suggestion_generated: bool = Field(alias="suggestionGenerated")
    suggestion_fallback_used: bool = Field(alias="suggestionFallbackUsed")
    model_call_attempted: bool = Field(alias="modelCallAttempted")
    model_call_succeeded: bool = Field(alias="modelCallSucceeded")
