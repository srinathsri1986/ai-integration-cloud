from fastapi import APIRouter

from app.models.connectors import (
    ConnectorListItem,
    NetSuiteConnectionTestResponse,
    NetSuiteConnectorConfig,
    NetSuiteConnectorConfigUpdate,
)
from app.services.connector_config_service import connector_config_service

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=list[ConnectorListItem])
def list_connectors() -> list[ConnectorListItem]:
    return connector_config_service.list_connectors()


@router.get("/netsuite", response_model=NetSuiteConnectorConfig)
def get_netsuite_config() -> NetSuiteConnectorConfig:
    return connector_config_service.get_netsuite_config()


@router.post("/netsuite/test", response_model=NetSuiteConnectionTestResponse)
def test_netsuite_connection() -> NetSuiteConnectionTestResponse:
    return connector_config_service.test_netsuite_connection()


@router.put("/netsuite/config", response_model=NetSuiteConnectorConfig)
def update_netsuite_config(
    update: NetSuiteConnectorConfigUpdate,
) -> NetSuiteConnectorConfig:
    return connector_config_service.update_netsuite_config(update)
