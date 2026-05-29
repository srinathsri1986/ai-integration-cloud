from app.connectors.netsuite.interface import NetSuiteConnector
from app.connectors.netsuite.mock_connector import MockNetSuiteConnector
from app.connectors.netsuite.sandbox_connector import (
    NetSuiteSandboxConnectionConfig,
    NetSuiteSandboxConnector,
)
from app.core.config import get_settings


def make_netsuite_connector() -> NetSuiteConnector:
    settings = get_settings()

    if settings.netsuite_mode == "sandbox":
        return NetSuiteSandboxConnector(
            NetSuiteSandboxConnectionConfig(
                account_id=settings.netsuite_account_id,
                base_url=settings.netsuite_base_url,
                consumer_key=settings.netsuite_consumer_key,
                consumer_secret=settings.netsuite_consumer_secret,
                token_id=settings.netsuite_token_id,
                token_secret=settings.netsuite_token_secret,
                timeout_seconds=settings.netsuite_timeout_seconds,
            )
        )

    return MockNetSuiteConnector()
