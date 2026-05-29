from typing import Literal

from pydantic import BaseModel, Field


ConnectorEnvironment = Literal["sandbox", "production"]
ConnectorAuthMode = Literal["placeholder"]
ConnectorStatus = Literal["not_configured", "configured", "test_passed", "test_failed"]


class ConnectorListItem(BaseModel):
    id: Literal["netsuite"]
    name: str
    status: ConnectorStatus
    mock_mode: bool = Field(alias="mockMode")
    last_tested_at: str | None = Field(default=None, alias="lastTestedAt")


class NetSuiteConnectorConfig(BaseModel):
    account_id: str = Field(alias="accountId", min_length=3, max_length=64)
    environment: ConnectorEnvironment
    auth_mode: ConnectorAuthMode = Field(alias="authMode")
    mock_mode: bool = Field(alias="mockMode")
    status: ConnectorStatus
    last_tested_at: str | None = Field(default=None, alias="lastTestedAt")


class NetSuiteConnectorConfigUpdate(BaseModel):
    account_id: str = Field(alias="accountId", min_length=3, max_length=64)
    environment: ConnectorEnvironment
    auth_mode: ConnectorAuthMode = Field(alias="authMode")
    mock_mode: bool = Field(alias="mockMode")


class NetSuiteConnectionTestResponse(BaseModel):
    connector_id: Literal["netsuite"] = Field(alias="connectorId")
    success: bool
    status: ConnectorStatus
    message: str
    tested_at: str = Field(alias="testedAt")
    mock_mode: bool = Field(alias="mockMode")
