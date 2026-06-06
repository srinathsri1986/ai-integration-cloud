from datetime import UTC, datetime
import re
from threading import Lock
from time import perf_counter
from typing import Any
from uuid import uuid4

from app.models.connectors import (
    ConnectorListItem,
    NetSuiteConnectionTestResponse,
    NetSuiteConnectorConfig,
    NetSuiteConnectorConfigUpdate,
    RestApiApprovedObject,
    RestApiConnectionTestResponse,
    RestApiConnectorConfig,
    RestApiConnectorConfigUpdate,
    RestApiDiscoveredField,
    RestApiSchemaDiscoveryRequest,
    RestApiSchemaDiscoveryResponse,
    RestApiSchemaPromotionRequest,
    RestApiSchemaPromotionResponse,
)
from app.models.mapping import MappingObject
from app.connectors.netsuite.live_connector_stub import (
    NetSuiteSandboxConnectionConfig,
    NetSuiteSandboxConnector,
)
from app.core.config import get_settings
from app.services.audit_service import audit_service
from app.services.mapping_catalog import promote_mapping_object


_SECRET_FIELD_TERMS = ("password", "secret", "token", "apikey", "api_key", "authorization", "bearer")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


class ConnectorConfigService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._netsuite_config = self._default_config()
        self._rest_api_config = self._default_rest_api_config()

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

    def _default_rest_api_config(self) -> RestApiConnectorConfig:
        return RestApiConnectorConfig(
            connectorId="rest-api",
            displayName="Generic REST API",
            baseUrlPlaceholder="https://api.example.com",
            authMode="placeholder",
            mockMode=True,
            mode="mock",
            status="not_configured",
            lastTestedAt=None,
            baseUrlConfigured=False,
            credentialsConfigured=False,
            approvedObjects=["customer", "invoice", "opportunity"],
            approvedActions=["read_sample", "validate_payload", "simulate_post_placeholder"],
        )

    def approved_rest_api_objects(self) -> list[RestApiApprovedObject]:
        return [
            RestApiApprovedObject(
                objectId="customer",
                label="Customer",
                description="Approved customer profile shape for CRM, ERP, and support APIs.",
                fields=[
                    {"name": "externalId", "label": "External ID", "type": "string", "required": True},
                    {"name": "displayName", "label": "Display name", "type": "string", "required": True},
                    {"name": "status", "label": "Status", "type": "string", "required": False},
                    {"name": "region", "label": "Region", "type": "string", "required": False},
                ],
            ),
            RestApiApprovedObject(
                objectId="invoice",
                label="Invoice",
                description="Approved invoice header shape for finance integration mappings.",
                fields=[
                    {"name": "invoiceNumber", "label": "Invoice number", "type": "string", "required": True},
                    {"name": "customerExternalId", "label": "Customer external ID", "type": "string", "required": True},
                    {"name": "amount", "label": "Amount", "type": "number", "required": True},
                    {"name": "invoiceDate", "label": "Invoice date", "type": "date", "required": True},
                ],
            ),
            RestApiApprovedObject(
                objectId="opportunity",
                label="Opportunity",
                description="Approved opportunity shape for pipeline-to-finance handoffs.",
                fields=[
                    {"name": "opportunityId", "label": "Opportunity ID", "type": "string", "required": True},
                    {"name": "accountName", "label": "Account name", "type": "string", "required": True},
                    {"name": "amount", "label": "Amount", "type": "number", "required": False},
                    {"name": "closeDate", "label": "Close date", "type": "date", "required": False},
                ],
            ),
        ]

    def discover_rest_api_schema(
        self,
        request: RestApiSchemaDiscoveryRequest,
    ) -> RestApiSchemaDiscoveryResponse:
        fields: list[RestApiDiscoveredField] = []
        warnings: list[str] = []

        for name, sample in list(request.sample_payload.items())[:50]:
            normalized_name = name.lower().replace("-", "_")
            compact_name = normalized_name.replace("_", "")
            if any(term in compact_name or term in normalized_name for term in _SECRET_FIELD_TERMS):
                warnings.append(f"{name} was skipped because it looks like a secret or credential field.")
                continue

            if isinstance(sample, dict | list):
                warnings.append(f"{name} was skipped because V3.0 discovery supports top-level scalar fields only.")
                continue

            fields.append(
                RestApiDiscoveredField(
                    name=name,
                    label=self._label_from_field_name(name),
                    type=self._infer_rest_field_type(sample),
                    required=sample is not None,
                    sample=sample,
                )
            )

        if len(fields) == 0:
            warnings.append("No usable scalar fields were discovered from the sample payload.")

        return RestApiSchemaDiscoveryResponse(
            connectorId="rest-api",
            objectId=self._object_id_from_label(request.object_label),
            objectLabel=request.object_label,
            mode="schema_discovery",
            fields=fields[:24],
            warnings=warnings,
            generatedFromSample=True,
            executable=False,
        )

    def promote_rest_api_schema(
        self,
        request: RestApiSchemaPromotionRequest,
    ) -> RestApiSchemaPromotionResponse:
        request_id = str(uuid4())
        started = perf_counter()
        success = False
        warnings: list[str] = []

        try:
            safe_fields = []
            for field in request.fields:
                normalized_name = field.name.lower().replace("-", "_")
                compact_name = normalized_name.replace("_", "")
                if any(term in compact_name or term in normalized_name for term in _SECRET_FIELD_TERMS):
                    warnings.append(f"{field.name} was skipped because it looks like a secret or credential field.")
                    continue

                safe_fields.append(
                    {
                        "name": field.name,
                        "description": f"Promoted from governed REST sample discovery as {field.type}.",
                        "type": field.type,
                        "required": field.required,
                        "sample": field.sample,
                    }
                )

            if len(safe_fields) == 0:
                raise ValueError("At least one safe field is required to promote a REST schema.")

            mapping_object = MappingObject(
                id=f"rest-governed-{request.object_id.removeprefix('rest-discovered-')}",
                displayName=request.object_label,
                systemId="rest-api",
                fields=safe_fields,
            )
            promoted = promote_mapping_object(mapping_object)
            success = True

            return RestApiSchemaPromotionResponse(
                connectorId="rest-api",
                promoted=True,
                objectId=promoted.id,
                objectLabel=promoted.display_name,
                mappingObject=promoted,
                message=f"{promoted.display_name} promoted as a governed REST catalog object.",
                warnings=warnings,
            )
        finally:
            audit_service.record_connector_action(
                request_id=request_id,
                action="schema_promotion",
                connector_id="rest-api",
                endpoint_called="/api/v1/connectors/rest-api/promote-schema",
                success=success,
                latency_ms=int((perf_counter() - started) * 1000),
            )

    def _infer_rest_field_type(self, sample: Any) -> str:
        if isinstance(sample, bool):
            return "boolean"
        if isinstance(sample, int | float) and not isinstance(sample, bool):
            return "number"
        if isinstance(sample, str) and _DATE_PATTERN.match(sample):
            return "date"
        return "string"

    def _label_from_field_name(self, name: str) -> str:
        words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).replace("_", " ").replace("-", " ")
        return words.strip().title() or name

    def _object_id_from_label(self, label: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        return f"rest-discovered-{slug or 'object'}"

    def list_connectors(self) -> list[ConnectorListItem]:
        netsuite_config = self.get_netsuite_config()
        rest_api_config = self.get_rest_api_config()
        return [
            ConnectorListItem(
                id="netsuite",
                name="NetSuite",
                status=netsuite_config.status,
                mockMode=netsuite_config.mock_mode,
                mode=netsuite_config.mode,
                lastTestedAt=netsuite_config.last_tested_at,
            ),
            ConnectorListItem(
                id="rest-api",
                name="REST API",
                status=rest_api_config.status,
                mockMode=rest_api_config.mock_mode,
                mode=rest_api_config.mode,
                lastTestedAt=rest_api_config.last_tested_at,
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

    def get_rest_api_config(self) -> RestApiConnectorConfig:
        with self._lock:
            return self._rest_api_config.model_copy()

    def update_rest_api_config(
        self,
        update: RestApiConnectorConfigUpdate,
    ) -> RestApiConnectorConfig:
        with self._lock:
            self._rest_api_config = self._rest_api_config.model_copy(
                update={
                    "display_name": update.display_name,
                    "base_url_placeholder": update.base_url_placeholder,
                    "auth_mode": update.auth_mode,
                    "mock_mode": True,
                    "mode": "mock",
                    "status": "configured",
                    "base_url_configured": False,
                    "credentials_configured": False,
                }
            )
            return self._rest_api_config.model_copy()

    def test_rest_api_connection(self) -> RestApiConnectionTestResponse:
        request_id = str(uuid4())
        started = perf_counter()
        tested_at = datetime.now(UTC).isoformat()
        success = False

        try:
            with self._lock:
                self._rest_api_config = self._rest_api_config.model_copy(
                    update={"status": "test_passed", "last_tested_at": tested_at}
                )
                config = self._rest_api_config.model_copy()

            success = True
            return RestApiConnectionTestResponse(
                connectorId="rest-api",
                success=success,
                status=config.status,
                message=(
                    "Mock REST API connector test passed. No outbound HTTP request was made. "
                    "No credentials were used or stored."
                ),
                testedAt=tested_at,
                mockMode=config.mock_mode,
                mode=config.mode,
                baseUrlConfigured=config.base_url_configured,
                credentialsConfigured=config.credentials_configured,
                approvedObjects=config.approved_objects,
                approvedActions=config.approved_actions,
            )
        finally:
            latency_ms = int((perf_counter() - started) * 1000)
            audit_service.record_connector_action(
                request_id=request_id,
                action="test_connection",
                connector_id="rest-api",
                endpoint_called="/api/v1/connectors/rest-api/test",
                success=success,
                latency_ms=latency_ms,
            )

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
            self._rest_api_config = self._default_rest_api_config()


connector_config_service = ConnectorConfigService()
