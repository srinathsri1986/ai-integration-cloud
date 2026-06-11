from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.models.mapping import MappingObject


ConnectorEnvironment = Literal["sandbox", "production"]
ConnectorMode = Literal["mock", "sandbox"]
ConnectorAuthMode = Literal["placeholder", "token_based_auth"]
ConnectorConfigAuthMode = Literal["placeholder"]
ConnectorStatus = Literal["not_configured", "configured", "test_passed", "test_failed"]
ConnectorId = Literal["netsuite", "rest-api"]
RestApiObjectId = Literal["customer", "invoice", "opportunity"]
RestApiActionId = Literal["read_sample", "validate_payload", "simulate_post_placeholder"]


class ConnectorListItem(BaseModel):
    id: ConnectorId
    name: str
    status: ConnectorStatus
    mock_mode: bool = Field(alias="mockMode")
    mode: ConnectorMode
    last_tested_at: str | None = Field(default=None, alias="lastTestedAt")


class NetSuiteConnectorConfig(BaseModel):
    account_id: str = Field(alias="accountId", min_length=3, max_length=64)
    environment: ConnectorEnvironment
    auth_mode: ConnectorAuthMode = Field(alias="authMode")
    mock_mode: bool = Field(alias="mockMode")
    mode: ConnectorMode
    status: ConnectorStatus
    last_tested_at: str | None = Field(default=None, alias="lastTestedAt")
    base_url_configured: bool = Field(default=False, alias="baseUrlConfigured")
    credentials_configured: bool = Field(default=False, alias="credentialsConfigured")


class NetSuiteConnectorConfigUpdate(BaseModel):
    account_id: str = Field(alias="accountId", min_length=3, max_length=64)
    environment: ConnectorEnvironment
    auth_mode: ConnectorConfigAuthMode = Field(alias="authMode")
    mock_mode: bool = Field(alias="mockMode")


class ConnectorTestResult(BaseModel):
    """Normalised response shape returned by POST /{connector_id}/test.

    Every connector plugin must return at minimum ``ok`` and ``message``.
    The optional ``mode`` key ("mock" / "sandbox" / "live") is preserved when
    the plugin provides it; it defaults to "mock" for plugins that don't.
    """

    ok: bool
    mode: str = "mock"
    message: str


class NetSuiteConnectionTestResponse(BaseModel):
    connector_id: Literal["netsuite"] = Field(alias="connectorId")
    success: bool
    status: ConnectorStatus
    message: str
    tested_at: str = Field(alias="testedAt")
    mock_mode: bool = Field(alias="mockMode")
    mode: ConnectorMode
    base_url_configured: bool = Field(alias="baseUrlConfigured")
    credentials_configured: bool = Field(alias="credentialsConfigured")


class RestApiObjectField(BaseModel):
    name: str
    label: str
    type: Literal["string", "number", "boolean", "date"]
    required: bool = False


class RestApiApprovedObject(BaseModel):
    object_id: RestApiObjectId = Field(alias="objectId")
    label: str
    description: str
    fields: list[RestApiObjectField]


class RestApiConnectorConfig(BaseModel):
    connector_id: Literal["rest-api"] = Field(alias="connectorId")
    display_name: str = Field(alias="displayName", min_length=3, max_length=80)
    base_url_placeholder: str = Field(alias="baseUrlPlaceholder", min_length=3, max_length=120)
    auth_mode: ConnectorConfigAuthMode = Field(alias="authMode")
    mock_mode: bool = Field(alias="mockMode")
    mode: Literal["mock"]
    status: ConnectorStatus
    last_tested_at: str | None = Field(default=None, alias="lastTestedAt")
    base_url_configured: bool = Field(default=False, alias="baseUrlConfigured")
    credentials_configured: bool = Field(default=False, alias="credentialsConfigured")
    approved_objects: list[RestApiObjectId] = Field(alias="approvedObjects")
    approved_actions: list[RestApiActionId] = Field(alias="approvedActions")


class RestApiConnectorConfigUpdate(BaseModel):
    display_name: str = Field(alias="displayName", min_length=3, max_length=80)
    base_url_placeholder: str = Field(alias="baseUrlPlaceholder", min_length=3, max_length=120)
    auth_mode: ConnectorConfigAuthMode = Field(alias="authMode")
    mock_mode: bool = Field(alias="mockMode")


class RestApiConnectionTestResponse(BaseModel):
    connector_id: Literal["rest-api"] = Field(alias="connectorId")
    success: bool
    status: ConnectorStatus
    message: str
    tested_at: str = Field(alias="testedAt")
    mock_mode: bool = Field(alias="mockMode")
    mode: Literal["mock"]
    base_url_configured: bool = Field(alias="baseUrlConfigured")
    credentials_configured: bool = Field(alias="credentialsConfigured")
    approved_objects: list[RestApiObjectId] = Field(alias="approvedObjects")
    approved_actions: list[RestApiActionId] = Field(alias="approvedActions")


class RestApiSchemaDiscoveryRequest(BaseModel):
    object_label: str = Field(alias="objectLabel", min_length=3, max_length=80)
    sample_payload: dict[str, Any] = Field(alias="samplePayload")

    @field_validator("object_label")
    @classmethod
    def reject_sensitive_label(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["password", "secret", "token", "api key", "authorization", "bearer"]
        if any(term in normalized for term in blocked):
            raise ValueError("REST object labels cannot contain secret-like terms.")

        return value

    @field_validator("sample_payload")
    @classmethod
    def require_bounded_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("Sample payload must include at least one field.")
        if len(value) > 50:
            raise ValueError("Sample payload can include at most 50 top-level fields.")

        return value


class RestApiDiscoveredField(BaseModel):
    name: str
    label: str
    type: Literal["string", "number", "boolean", "date"]
    required: bool
    sample: str | int | float | bool | None = None


class RestApiSchemaDiscoveryResponse(BaseModel):
    connector_id: Literal["rest-api"] = Field(alias="connectorId")
    object_id: str = Field(alias="objectId")
    object_label: str = Field(alias="objectLabel")
    mode: Literal["schema_discovery"]
    fields: list[RestApiDiscoveredField]
    warnings: list[str]
    generated_from_sample: bool = Field(alias="generatedFromSample")
    executable: bool


class RestApiSchemaPromotionRequest(BaseModel):
    object_id: str = Field(alias="objectId", min_length=3, max_length=80, pattern=r"^[a-z0-9-]+$")
    object_label: str = Field(alias="objectLabel", min_length=3, max_length=80)
    fields: list[RestApiDiscoveredField] = Field(min_length=1, max_length=24)

    @field_validator("object_label")
    @classmethod
    def reject_sensitive_label(cls, value: str) -> str:
        normalized = value.lower()
        blocked = ["password", "secret", "token", "api key", "authorization", "bearer"]
        if any(term in normalized for term in blocked):
            raise ValueError("REST object labels cannot contain secret-like terms.")

        return value


class RestApiSchemaPromotionResponse(BaseModel):
    connector_id: Literal["rest-api"] = Field(alias="connectorId")
    promoted: bool
    object_id: str = Field(alias="objectId")
    object_label: str = Field(alias="objectLabel")
    mapping_object: MappingObject = Field(alias="mappingObject")
    message: str
    warnings: list[str]


# ---------------------------------------------------------------------------
# Live schema discovery models — Release 13.0
# ---------------------------------------------------------------------------

class ConnectorSchemaField(BaseModel):
    """A single field within a connector schema object."""
    name: str
    label: str
    type: str          # string | number | date | boolean | id | reference
    required: bool = False
    updateable: bool = True
    sample: str | None = None


class ConnectorSchemaObject(BaseModel):
    """A table / sObject / resource with its field list."""
    objectId: str
    label: str
    fields: list[ConnectorSchemaField]


class ConnectorSchema(BaseModel):
    """Full schema response for a connector — returned by GET /connectors/{id}/schema."""
    connectorId: str
    mode: str          # live | mock
    objects: list[ConnectorSchemaObject]
    fetchedAt: str
