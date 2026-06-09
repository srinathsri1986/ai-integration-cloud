from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


MappingFieldType = Literal["string", "number", "date", "boolean"]

# R22b: live schema field shape from GET /api/v1/connectors/{id}/schema.
# A superset of MappingField — accepts any type string from the connector layer.
class LiveSchemaField(BaseModel):
    name: str
    label: str
    type: str  # connector-native type string e.g. "string", "currency", "reference"
    required: bool = False
    sample: str | int | float | bool | None = None
MappingTransform = Literal[
    "direct",
    "rename",
    "format_date",
    "lookup_placeholder",
    "constant_placeholder",
]
MappingDefinitionStatus = Literal["draft", "pending_approval", "approved", "published", "paused"]
MappingLifecycleAction = Literal["submit_for_approval", "approve", "reject", "publish", "pause"]


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
    require_live_ai: bool = Field(default=False, alias="requireLiveAi")
    # R22b: optional live schema fields from the connector schema API.
    # When provided, the AI reasons over these real fields instead of the static catalog.
    source_fields: list[LiveSchemaField] | None = Field(default=None, alias="sourceFields")
    target_fields: list[LiveSchemaField] | None = Field(default=None, alias="targetFields")

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


class MappingDefinitionRow(BaseModel):
    id: str
    source_field: str = Field(alias="sourceField")
    target_field: str = Field(alias="targetField")
    transform: MappingTransform
    confidence: float | None = Field(default=None, ge=0, le=1)
    rationale: str | None = Field(default=None, max_length=240)


class MappingDefinition(BaseModel):
    mapping_id: str = Field(alias="mappingId")
    name: str
    description: str
    source_object_id: str = Field(alias="sourceObjectId")
    target_object_id: str = Field(alias="targetObjectId")
    status: MappingDefinitionStatus
    mappings: list[MappingDefinitionRow]
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")


class MappingDefinitionUpsertRequest(BaseModel):
    mapping_id: str = Field(alias="mappingId", min_length=3, max_length=96, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=500)
    source_object_id: str = Field(alias="sourceObjectId", min_length=3, max_length=80)
    target_object_id: str = Field(alias="targetObjectId", min_length=3, max_length=80)
    status: MappingDefinitionStatus = "draft"
    mappings: list[MappingDefinitionRow] = Field(min_length=1, max_length=50)

    @field_validator("description", "name")
    @classmethod
    def reject_raw_query_language(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["select *", "suiteql", "sql query", "raw query", "script execution", "password", "secret"]
        if any(term in normalized for term in blocked):
            raise ValueError("Mapping definitions cannot contain raw query, code, or secret language.")

        return value

    @field_validator("status")
    @classmethod
    def require_lifecycle_for_non_draft_status(
        cls,
        value: MappingDefinitionStatus,
    ) -> MappingDefinitionStatus:
        if value != "draft":
            raise ValueError("Mapping definitions must be saved as draft before lifecycle actions.")

        return value


class MappingLifecycleRequest(BaseModel):
    action: MappingLifecycleAction
    note: str | None = Field(default=None, max_length=300)


class MappingLifecycleResponse(BaseModel):
    mapping: MappingDefinition
    action: MappingLifecycleAction
    message: str


class MappingSimulationResponse(BaseModel):
    mapping_id: str = Field(alias="mappingId")
    status: MappingDefinitionStatus
    source_object_id: str = Field(alias="sourceObjectId")
    target_object_id: str = Field(alias="targetObjectId")
    source_payload: dict[str, Any] = Field(alias="sourcePayload")
    target_payload: dict[str, Any] = Field(alias="targetPayload")
    warnings: list[str]
    transforms_applied: list[str] = Field(alias="transformsApplied")
    simulated_at: str = Field(alias="simulatedAt")


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
