from fastapi import APIRouter

from app.models.audit import AuditLogEntry, AuditLogSummary
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogEntry])
def logs() -> list[AuditLogEntry]:
    return audit_service.list_logs()


@router.get("/summary", response_model=AuditLogSummary)
def summary() -> AuditLogSummary:
    return audit_service.summary()
