import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.auth import require_permissions
from app.models.audit import AuditLogEntry, AuditLogSummary, AuditMetrics
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])

# ---------------------------------------------------------------------------
# Logs endpoint (with date-range + intent filters)
# ---------------------------------------------------------------------------


@router.get("/logs", response_model=list[AuditLogEntry])
def logs(
    request_id: Annotated[str | None, Query(alias="requestId")] = None,
    intent: str | None = None,
    provider: str | None = None,
    success: bool | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 100,
    offset: int = 0,
    user=Depends(require_permissions("audit:read")),
) -> list[AuditLogEntry]:
    """Return filtered audit log entries.

    - **intent**: exact match on ``detectedIntent`` field
    - **since** / **until**: ISO date strings (``YYYY-MM-DD``) for date-range filtering
    - **success**: true | false
    """
    return audit_service.list_logs(
        tenant_id=user.tenant_id,
        request_id=request_id,
        intent=intent,
        provider=provider,
        success=success,
        since=since,
        until=until,
        limit=min(max(limit, 1), 500),
        offset=max(offset, 0),
    )


# ---------------------------------------------------------------------------
# Summary endpoint (existing — unchanged)
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=AuditLogSummary)
def summary(user=Depends(require_permissions("audit:read"))) -> AuditLogSummary:
    return audit_service.summary(tenant_id=user.tenant_id)


# ---------------------------------------------------------------------------
# Metrics endpoint — per-day timeseries, by-intent, by-connector, latency stats
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=AuditMetrics)
def metrics(
    days: int = 30,
    user=Depends(require_permissions("audit:read")),
) -> AuditMetrics:
    """Return aggregate observability metrics for the last *days* calendar days.

    Response includes:
    - ``totalEvents``, ``successRate``, ``averageLatencyMs``, ``p50LatencyMs``, ``p95LatencyMs``
    - ``byIntent`` — event count keyed by detected intent
    - ``byConnector`` — event count keyed by connector id (inferred from tools_used)
    - ``eventsPerDay`` — list of ``{date, total, successes, failures}`` for chart rendering
    - ``distinctIntents`` — sorted list of known intents (for filter dropdowns)
    """
    return audit_service.metrics(
        tenant_id=user.tenant_id,
        days=min(max(days, 1), 365),
    )


# ---------------------------------------------------------------------------
# CSV export — full audit log download
# ---------------------------------------------------------------------------

_CSV_HEADERS = [
    "timestamp", "requestId", "detectedIntent", "user", "channel",
    "success", "failureReason", "latencyMs", "endpointCalled",
    "toolsUsed", "aiProvider", "aiMode", "modelName",
    "modelCallAttempted", "modelCallSucceeded",
    "narrativeGenerated", "fallbackUsed",
]


def _log_to_row(log: AuditLogEntry) -> list[str]:
    return [
        log.timestamp or "",
        log.request_id or "",
        log.detected_intent or "",
        log.user or "",
        log.channel or "",
        str(log.success),
        log.failure_reason or "",
        str(log.latency_ms),
        log.endpoint_called or "",
        "|".join(log.tools_used or []),
        log.ai_provider or "",
        log.ai_mode or "",
        log.model_name or "",
        str(log.model_call_attempted),
        str(log.model_call_succeeded),
        str(log.narrative_generated),
        str(log.fallback_used),
    ]


@router.get("/export.csv")
def export_csv(
    intent: str | None = None,
    success: bool | None = None,
    since: str | None = None,
    until: str | None = None,
    user=Depends(require_permissions("audit:read")),
) -> StreamingResponse:
    """Stream a CSV download of the audit log (up to 5 000 rows).

    Supports the same filters as ``/audit/logs``.
    """
    entries = audit_service.list_logs(
        tenant_id=user.tenant_id,
        intent=intent,
        success=success,
        since=since,
        until=until,
        limit=5000,
        offset=0,
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(_CSV_HEADERS)
    for log in entries:
        writer.writerow(_log_to_row(log))

    filename = f"audit-log-{(since or 'all')}-to-{(until or 'today')}.csv"
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
