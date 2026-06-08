"""Repository for webhook_deliveries table — Release 12.0."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import WebhookDeliveryRecord
from app.models.webhooks import WebhookDelivery, WebhookDeliveryStats


class WebhookDeliveryRepository:
    def __init__(self, session: Session, tenant_id: int | None = None) -> None:
        self.session = session
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def create(
        self,
        delivery_id: str,
        flow_id: str,
        payload_hash: str,
        request_id: str,
        tenant_id: int | None = None,
        max_attempts: int = 3,
        event_id: str | None = None,
        event_source: str | None = None,
        event_type: str | None = None,
        event_spec_version: str | None = None,
    ) -> WebhookDelivery:
        now = datetime.now(UTC).isoformat()
        record = WebhookDeliveryRecord(
            delivery_id=delivery_id,
            flow_id=flow_id,
            tenant_id=tenant_id,
            payload_hash=payload_hash,
            status="processing",
            attempt_count=1,
            max_attempts=max_attempts,
            request_id=request_id,
            received_at=now,
            event_id=event_id,
            event_source=event_source,
            event_type=event_type,
            event_spec_version=event_spec_version,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self._to_model(record)

    def mark_succeeded(self, delivery_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        self.session.execute(
            update(WebhookDeliveryRecord)
            .where(WebhookDeliveryRecord.delivery_id == delivery_id)
            .values(status="succeeded", completed_at=now, last_error=None,
                    updated_at=datetime.now(UTC))
        )
        self.session.commit()

    def mark_failed(
        self,
        delivery_id: str,
        error: str,
        increment_attempt: bool = True,
        next_retry_at: str | None = None,
    ) -> None:
        record = self._get_record(delivery_id)
        if record is None:
            return
        new_attempt = record.attempt_count + (1 if increment_attempt else 0)
        self.session.execute(
            update(WebhookDeliveryRecord)
            .where(WebhookDeliveryRecord.delivery_id == delivery_id)
            .values(
                status="failed",
                attempt_count=new_attempt,
                last_error=str(error)[:1000],
                next_retry_at=next_retry_at,
                updated_at=datetime.now(UTC),
            )
        )
        self.session.commit()

    def mark_dead_letter(self, delivery_id: str, error: str) -> None:
        now = datetime.now(UTC).isoformat()
        record = self._get_record(delivery_id)
        if record is None:
            return
        new_attempt = record.attempt_count + 1
        self.session.execute(
            update(WebhookDeliveryRecord)
            .where(WebhookDeliveryRecord.delivery_id == delivery_id)
            .values(
                status="dead_letter",
                attempt_count=new_attempt,
                last_error=str(error)[:1000],
                completed_at=now,
                next_retry_at=None,
                updated_at=datetime.now(UTC),
            )
        )
        self.session.commit()

    def mark_retrying(self, delivery_id: str, new_request_id: str) -> None:
        """Reset a dead-letter or failed delivery for manual retry."""
        self.session.execute(
            update(WebhookDeliveryRecord)
            .where(WebhookDeliveryRecord.delivery_id == delivery_id)
            .values(
                status="processing",
                request_id=new_request_id,
                last_error=None,
                next_retry_at=None,
                completed_at=None,
                updated_at=datetime.now(UTC),
            )
        )
        self.session.commit()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get(self, delivery_id: str) -> WebhookDelivery | None:
        record = self._get_record(delivery_id)
        return self._to_model(record) if record else None

    def list_for_flow(
        self, flow_id: str, limit: int = 50
    ) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDeliveryRecord)
            .where(WebhookDeliveryRecord.flow_id == flow_id)
            .order_by(WebhookDeliveryRecord.created_at.desc())
            .limit(limit)
        )
        return [self._to_model(r) for r in self.session.scalars(stmt).all()]

    def list_all(
        self,
        status: str | None = None,
        flow_id: str | None = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        stmt = (
            select(WebhookDeliveryRecord)
            .order_by(WebhookDeliveryRecord.created_at.desc())
        )
        if status:
            stmt = stmt.where(WebhookDeliveryRecord.status == status)
        if flow_id:
            stmt = stmt.where(WebhookDeliveryRecord.flow_id == flow_id)
        stmt = stmt.limit(limit)
        return [self._to_model(r) for r in self.session.scalars(stmt).all()]

    def stats(self) -> WebhookDeliveryStats:
        records = self.session.scalars(select(WebhookDeliveryRecord)).all()
        return WebhookDeliveryStats(
            total=len(records),
            succeeded=sum(1 for r in records if r.status == "succeeded"),
            failed=sum(1 for r in records if r.status == "failed"),
            deadLetter=sum(1 for r in records if r.status == "dead_letter"),
            processing=sum(1 for r in records if r.status == "processing"),
        )

    def dead_letter_count(self) -> int:
        return sum(
            1
            for r in self.session.scalars(
                select(WebhookDeliveryRecord).where(
                    WebhookDeliveryRecord.status == "dead_letter"
                )
            ).all()
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_record(self, delivery_id: str) -> WebhookDeliveryRecord | None:
        return self.session.scalars(
            select(WebhookDeliveryRecord).where(
                WebhookDeliveryRecord.delivery_id == delivery_id
            )
        ).first()

    def _to_model(self, record: WebhookDeliveryRecord) -> WebhookDelivery:
        return WebhookDelivery(
            deliveryId=record.delivery_id,
            flowId=record.flow_id,
            receivedAt=record.received_at,
            payloadHash=record.payload_hash,
            status=record.status,
            attemptCount=record.attempt_count,
            maxAttempts=record.max_attempts,
            lastError=record.last_error,
            requestId=record.request_id,
            nextRetryAt=record.next_retry_at,
            completedAt=record.completed_at,
            eventId=record.event_id,
            eventSource=record.event_source,
            eventType=record.event_type,
            eventSpecVersion=record.event_spec_version,
        )
