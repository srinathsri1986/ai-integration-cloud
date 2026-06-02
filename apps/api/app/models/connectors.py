from typing import Literal

from pydantic import BaseModel, Field


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
