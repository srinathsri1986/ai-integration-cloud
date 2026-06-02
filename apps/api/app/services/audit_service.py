from datetime import UTC, datetime
from threading import Lock

from app.core.database import SessionLocal
from app.core.security import redact_mapping
from app.models.audit import AuditLogEntry, AuditLogSummary
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self) -> None:
        self._logs: list[AuditLogEntry] = []
        self._lock = Lock()

    def record(self, entry: AuditLogEntry) -> None:
        safe_entry = AuditLogEntry.model_validate(redact_mapping(entry.model_dump(by_alias=True)))
        with SessionLocal() as session:
            AuditRepository(session).append(safe_entry)

        with self._lock:
            self._logs.append(safe_entry)

    def record_connector_action(
        self,
        request_id: str,
        action: str,
        connector_id: str,
        endpoint_called: str,
        success: bool,
        latency_ms: int,
    ) -> None:
        self.record(
            AuditLogEntry(
                timestamp=datetime.now(UTC).isoformat(),
                requestId=request_id,
                user="local-dev-user",
                channel="web",
                question=f"Connector action: {connector_id}.{action}",
                detectedIntent="CONNECTOR_TEST",
                confidence=1,
                toolsUsed=[f"connector.{connector_id}.{action}"],
                endpointCalled=endpoint_called,
                fallbackUsed=False,
                success=success,
                failureReason=None if success else "ConnectorTestFailed",
                latencyMs=latency_ms,
                aiProvider="none",
                aiMode="disabled",
                modelName=None,
                modelCallAttempted=False,
                modelCallSucceeded=False,
                usedFallbackRouter=False,
                narrativeProvider="none",
                narrativeModel=None,
                narrativeGenerated=False,
                narrativeFallbackUsed=False,
            )
        )

    def record_flow_action(
        self,
        request_id: str,
        flow_id: str,
        endpoint_called: str,
        tools_used: list[str],
        success: bool,
        latency_ms: int,
    ) -> None:
        self.record(
            AuditLogEntry(
                timestamp=datetime.now(UTC).isoformat(),
                requestId=request_id,
                user="local-dev-user",
                channel="web",
                question=f"Flow run: {flow_id}",
                detectedIntent="FLOW_RUN",
                confidence=1,
                toolsUsed=tools_used,
                endpointCalled=endpoint_called,
                fallbackUsed=False,
                success=success,
                failureReason=None if success else "FlowRunFailed",
                latencyMs=latency_ms,
                aiProvider="none",
                aiMode="disabled",
                modelName=None,
                modelCallAttempted=False,
                modelCallSucceeded=False,
                usedFallbackRouter=False,
                narrativeProvider="none",
                narrativeModel=None,
                narrativeGenerated=False,
                narrativeFallbackUsed=False,
            )
        )

    def record_flow_definition_action(
        self,
        flow_id: str,
        action: str,
        tools_used: list[str],
    ) -> None:
        self.record(
            AuditLogEntry(
                timestamp=datetime.now(UTC).isoformat(),
                requestId=f"flow-definition-{flow_id}",
                user="local-dev-user",
                channel="web",
                question=f"Flow definition action: {flow_id}.{action}",
                detectedIntent="FLOW_DEFINITION",
                confidence=1,
                toolsUsed=tools_used,
                endpointCalled="/api/v1/flows/definitions",
                fallbackUsed=False,
                success=True,
                failureReason=None,
                latencyMs=0,
                aiProvider="none",
                aiMode="disabled",
                modelName=None,
                modelCallAttempted=False,
                modelCallSucceeded=False,
                usedFallbackRouter=False,
                narrativeProvider="none",
                narrativeModel=None,
                narrativeGenerated=False,
                narrativeFallbackUsed=False,
            )
        )

    def record_mapping_definition_action(
        self,
        mapping_id: str,
        action: str,
        tools_used: list[str],
    ) -> None:
        self.record(
            AuditLogEntry(
                timestamp=datetime.now(UTC).isoformat(),
                requestId=f"mapping-definition-{mapping_id}",
                user="local-dev-user",
                channel="web",
                question=f"Mapping definition action: {mapping_id}.{action}",
                detectedIntent="MAPPING_DEFINITION",
                confidence=1,
                toolsUsed=tools_used,
                endpointCalled="/api/v1/mappings/definitions",
                fallbackUsed=False,
                success=True,
                failureReason=None,
                latencyMs=0,
                aiProvider="none",
                aiMode="disabled",
                modelName=None,
                modelCallAttempted=False,
                modelCallSucceeded=False,
                usedFallbackRouter=False,
                narrativeProvider="none",
                narrativeModel=None,
                narrativeGenerated=False,
                narrativeFallbackUsed=False,
            )
        )

    def record_mapping_simulation_action(
        self,
        request_id: str,
        mapping_id: str,
        success: bool,
        latency_ms: int,
    ) -> None:
        self.record(
            AuditLogEntry(
                timestamp=datetime.now(UTC).isoformat(),
                requestId=request_id,
                user="local-dev-user",
                channel="web",
                question=f"Mapping simulation: {mapping_id}",
                detectedIntent="MAPPING_SIMULATION",
                confidence=1,
                toolsUsed=["mapping.simulate"],
                endpointCalled=f"/api/v1/mappings/definitions/{mapping_id}/simulate",
                fallbackUsed=False,
                success=success,
                failureReason=None if success else "MappingSimulationFailed",
                latencyMs=latency_ms,
                aiProvider="none",
                aiMode="disabled",
                modelName=None,
                modelCallAttempted=False,
                modelCallSucceeded=False,
                usedFallbackRouter=False,
                narrativeProvider="none",
                narrativeModel=None,
                narrativeGenerated=False,
                narrativeFallbackUsed=False,
            )
        )

    def list_logs(
        self,
        *,
        request_id: str | None = None,
        intent: str | None = None,
        provider: str | None = None,
        success: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        with SessionLocal() as session:
            return AuditRepository(session).list_logs(
                request_id=request_id,
                intent=intent,
                provider=provider,
                success=success,
                limit=limit,
                offset=offset,
            )

    def summary(self) -> AuditLogSummary:
        with SessionLocal() as session:
            return AuditRepository(session).summary()

    def clear_for_tests(self) -> None:
        with SessionLocal() as session:
            AuditRepository(session).clear()

        with self._lock:
            self._logs.clear()


audit_service = AuditService()
