from collections import Counter

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import AuditLogRecord
from app.models.audit import AuditLogEntry, AuditLogSummary


class AuditRepository:
    def __init__(self, session: Session, tenant_id: int | None = None) -> None:
        self.session = session
        self._tenant_id = tenant_id

    def append(self, entry: AuditLogEntry) -> None:
        record = AuditLogRecord(
            tenant_id=self._tenant_id,
            timestamp=entry.timestamp,
            request_id=entry.request_id,
            user=entry.user,
            channel=entry.channel,
            question=entry.question,
            detected_intent=entry.detected_intent,
            confidence=entry.confidence,
            tools_used=entry.tools_used,
            endpoint_called=entry.endpoint_called,
            fallback_used=entry.fallback_used,
            success=entry.success,
            failure_reason=entry.failure_reason,
            latency_ms=entry.latency_ms,
            ai_provider=entry.ai_provider,
            ai_mode=entry.ai_mode,
            model_name=entry.model_name,
            model_call_attempted=entry.model_call_attempted,
            model_call_succeeded=entry.model_call_succeeded,
            used_fallback_router=entry.used_fallback_router,
            narrative_provider=entry.narrative_provider,
            narrative_model=entry.narrative_model,
            narrative_generated=entry.narrative_generated,
            narrative_fallback_used=entry.narrative_fallback_used,
            metadata_json=entry.model_dump(by_alias=True),
        )
        self.session.add(record)
        self.session.commit()

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
        statement = select(AuditLogRecord).order_by(AuditLogRecord.created_at.desc())
        statement = self._scope(statement)

        if request_id:
            statement = statement.where(AuditLogRecord.request_id == request_id)
        if intent:
            statement = statement.where(AuditLogRecord.detected_intent == intent)
        if provider:
            statement = statement.where(AuditLogRecord.ai_provider == provider)
        if success is not None:
            statement = statement.where(AuditLogRecord.success.is_(success))

        statement = statement.limit(limit).offset(offset)
        records = self.session.scalars(statement).all()
        return [self._to_entry(record) for record in records]

    def summary(self) -> AuditLogSummary:
        statement = self._scope(select(AuditLogRecord))
        records = self.session.scalars(statement).all()
        total = len(records)
        successes = sum(1 for record in records if record.success)
        failures = total - successes
        fallback_count = sum(1 for record in records if record.fallback_used)
        average_latency_ms = (
            sum(record.latency_ms for record in records) / total if total else 0
        )
        by_intent = Counter(record.detected_intent for record in records)

        return AuditLogSummary(
            total=total,
            successes=successes,
            failures=failures,
            fallbackCount=fallback_count,
            averageLatencyMs=round(average_latency_ms, 2),
            byIntent=dict(by_intent),
        )

    def clear(self) -> None:
        self.session.execute(delete(AuditLogRecord))
        self.session.commit()

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(AuditLogRecord)) or 0

    def _scope(self, statement):
        if self._tenant_id is not None:
            statement = statement.where(
                (AuditLogRecord.tenant_id == self._tenant_id) | AuditLogRecord.tenant_id.is_(None)
            )
        return statement

    def _to_entry(self, record: AuditLogRecord) -> AuditLogEntry:
        return AuditLogEntry(
            timestamp=record.timestamp,
            requestId=record.request_id,
            user=record.user,
            channel=record.channel,
            question=record.question,
            detectedIntent=record.detected_intent,
            confidence=record.confidence,
            toolsUsed=record.tools_used,
            endpointCalled=record.endpoint_called,
            fallbackUsed=record.fallback_used,
            success=record.success,
            failureReason=record.failure_reason,
            latencyMs=record.latency_ms,
            aiProvider=record.ai_provider,
            aiMode=record.ai_mode,
            modelName=record.model_name,
            modelCallAttempted=record.model_call_attempted,
            modelCallSucceeded=record.model_call_succeeded,
            usedFallbackRouter=record.used_fallback_router,
            narrativeProvider=record.narrative_provider,
            narrativeModel=record.narrative_model,
            narrativeGenerated=record.narrative_generated,
            narrativeFallbackUsed=record.narrative_fallback_used,
        )
