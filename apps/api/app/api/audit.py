from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import require_permissions
from app.models.audit import AuditLogEntry, AuditLogSummary
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogEntry])
def logs(
    request_id: Annotated[str | None, Query(alias="requestId")] = None,
    intent: str | None = None,
    provider: str | None = None,
    success: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    user=Depends(require_permissions("audit:read")),
) -> list[AuditLogEntry]:
    return audit_service.list_logs(
        request_id=request_id,
        intent=intent,
        provider=provider,
        success=success,
        limit=min(max(limit, 1), 500),
        offset=max(offset, 0),
    )


@router.get("/summary", response_model=AuditLogSummary)
def summary(user=Depends(require_permissions("audit:read"))) -> AuditLogSummary:
    return audit_service.summary()
