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
from app.services.audit_service import audit_service


class ConnectorConfigService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._netsuite_config = NetSuiteConnectorConfig(
            accountId="MOCK-ACCOUNT",
            environment="sandbox",
            authMode="placeholder",
            mockMode=True,
            status="not_configured",
            lastTestedAt=None,
        )

    def list_connectors(self) -> list[ConnectorListItem]:
        config = self.get_netsuite_config()
        return [
            ConnectorListItem(
                id="netsuite",
                name="NetSuite",
                status=config.status,
                mockMode=config.mock_mode,
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
                status="configured",
                lastTestedAt=self._netsuite_config.last_tested_at,
            )
            return self._netsuite_config.model_copy()

    def test_netsuite_connection(self) -> NetSuiteConnectionTestResponse:
        request_id = str(uuid4())
        started = perf_counter()
        tested_at = datetime.now(UTC).isoformat()
        success = False

        try:
            with self._lock:
                self._netsuite_config = self._netsuite_config.model_copy(
                    update={"status": "test_passed", "last_tested_at": tested_at}
                )
                config = self._netsuite_config.model_copy()

            success = True
            return NetSuiteConnectionTestResponse(
                connectorId="netsuite",
                success=True,
                status=config.status,
                message="Mock NetSuite connection test passed. No credentials were used or stored.",
                testedAt=tested_at,
                mockMode=config.mock_mode,
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
            self._netsuite_config = NetSuiteConnectorConfig(
                accountId="MOCK-ACCOUNT",
                environment="sandbox",
                authMode="placeholder",
                mockMode=True,
                status="not_configured",
                lastTestedAt=None,
            )


connector_config_service = ConnectorConfigService()
