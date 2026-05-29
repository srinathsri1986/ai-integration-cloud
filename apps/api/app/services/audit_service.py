from collections import Counter
from datetime import UTC, datetime
from threading import Lock

from app.core.security import redact_mapping
from app.models.audit import AuditLogEntry, AuditLogSummary


class AuditService:
    def __init__(self) -> None:
        self._logs: list[AuditLogEntry] = []
        self._lock = Lock()

    def record(self, entry: AuditLogEntry) -> None:
        safe_entry = AuditLogEntry.model_validate(redact_mapping(entry.model_dump(by_alias=True)))
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

    def list_logs(self) -> list[AuditLogEntry]:
        with self._lock:
            return list(reversed(self._logs))

    def summary(self) -> AuditLogSummary:
        with self._lock:
            logs = list(self._logs)

        total = len(logs)
        successes = sum(1 for log in logs if log.success)
        failures = total - successes
        fallback_count = sum(1 for log in logs if log.fallback_used)
        average_latency_ms = sum(log.latency_ms for log in logs) / total if total else 0
        by_intent = Counter(log.detected_intent for log in logs)

        return AuditLogSummary(
            total=total,
            successes=successes,
            failures=failures,
            fallbackCount=fallback_count,
            averageLatencyMs=round(average_latency_ms, 2),
            byIntent=dict(by_intent),
        )

    def clear_for_tests(self) -> None:
        with self._lock:
            self._logs.clear()


audit_service = AuditService()
