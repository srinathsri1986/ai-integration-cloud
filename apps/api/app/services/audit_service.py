from collections import Counter
from threading import Lock

from app.models.audit import AuditLogEntry, AuditLogSummary


class AuditService:
    def __init__(self) -> None:
        self._logs: list[AuditLogEntry] = []
        self._lock = Lock()

    def record(self, entry: AuditLogEntry) -> None:
        with self._lock:
            self._logs.append(entry)

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
