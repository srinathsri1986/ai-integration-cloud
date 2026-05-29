from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from app.models.connectors import (
    ConnectorListItem,
    NetSuiteConnectionTestResponse,
    NetSuiteConnectorConfig,
    NetSuiteConnectorConfigUpdate,
)
from app.connectors.netsuite.sandbox_connector import (
    NetSuiteSandboxConnectionConfig,
    NetSuiteSandboxConnector,
)
from app.core.config import get_settings
from app.services.audit_service import audit_service


class ConnectorConfigService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._netsuite_config = self._default_config()

    def _default_config(self) -> NetSuiteConnectorConfig:
        settings = get_settings()
        mode = "sandbox" if settings.netsuite_mode == "sandbox" else "mock"
        auth_mode = "token_based_auth" if mode == "sandbox" else "placeholder"
        sandbox_config = self._sandbox_connection_config()

        return NetSuiteConnectorConfig(
            accountId=settings.netsuite_account_id if mode == "sandbox" else "MOCK-ACCOUNT",
            environment="sandbox",
            authMode=auth_mode,
            mockMode=mode == "mock",
            mode=mode,
            status="configured" if mode == "sandbox" else "not_configured",
            lastTestedAt=None,
            baseUrlConfigured=sandbox_config.base_url_configured,
            credentialsConfigured=sandbox_config.credentials_configured,
        )

    def _sandbox_connection_config(self) -> NetSuiteSandboxConnectionConfig:
        settings = get_settings()
        return NetSuiteSandboxConnectionConfig(
            account_id=settings.netsuite_account_id,
            base_url=settings.netsuite_base_url,
            consumer_key=settings.netsuite_consumer_key,
            consumer_secret=settings.netsuite_consumer_secret,
            token_id=settings.netsuite_token_id,
            token_secret=settings.netsuite_token_secret,
            timeout_seconds=settings.netsuite_timeout_seconds,
        )

    def list_connectors(self) -> list[ConnectorListItem]:
        config = self.get_netsuite_config()
        return [
            ConnectorListItem(
                id="netsuite",
                name="NetSuite",
                status=config.status,
                mockMode=config.mock_mode,
                mode=config.mode,
                lastTestedAt=config.last_tested_at,
            )
        ]

    def get_netsuite_config(self) -> NetSuiteConnectorConfig:
        with self._lock:
            return self._netsuite_config.model_copy()

    def update_netsuite_config(
        self,
        update: NetSuiteConnectorConfigUpdate,
    ) -> NetSuiteConnectorConfig:
        with self._lock:
            self._netsuite_config = NetSuiteConnectorConfig(
                accountId=update.account_id,
                environment=update.environment,
                authMode=update.auth_mode,
                mockMode=True,
                mode="mock",
                status="configured",
                lastTestedAt=self._netsuite_config.last_tested_at,
                baseUrlConfigured=False,
                credentialsConfigured=False,
            )
            return self._netsuite_config.model_copy()

    def test_netsuite_connection(self) -> NetSuiteConnectionTestResponse:
        request_id = str(uuid4())
        started = perf_counter()
        tested_at = datetime.now(UTC).isoformat()
        success = False

        try:
            current = self.get_netsuite_config()
            if current.mode == "sandbox":
                sandbox_connector = NetSuiteSandboxConnector(self._sandbox_connection_config())
                success, message = sandbox_connector.test_connection()
                status = "test_passed" if success else "test_failed"
            else:
                success = True
                status = "test_passed"
                message = "Mock NetSuite connection test passed. No credentials were used or stored."

            with self._lock:
                self._netsuite_config = self._netsuite_config.model_copy(
                    update={"status": status, "last_tested_at": tested_at}
                )
                config = self._netsuite_config.model_copy()

            return NetSuiteConnectionTestResponse(
                connectorId="netsuite",
                success=success,
                status=config.status,
                message=message,
                testedAt=tested_at,
                mockMode=config.mock_mode,
                mode=config.mode,
                baseUrlConfigured=config.base_url_configured,
                credentialsConfigured=config.credentials_configured,
            )
        finally:
            latency_ms = int((perf_counter() - started) * 1000)
            audit_service.record_connector_action(
                request_id=request_id,
                action="test_connection",
                connector_id="netsuite",
                endpoint_called="/api/v1/connectors/netsuite/test",
                success=success,
                latency_ms=latency_ms,
            )

    def clear_for_tests(self) -> None:
        with self._lock:
            self._netsuite_config = self._default_config()


connector_config_service = ConnectorConfigService()
