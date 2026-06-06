"""Celery tasks — Release 12.0: webhook delivery tracking integrated.

execute_flow_task now accepts an optional delivery_id. When present it:
  - marks the delivery succeeded on completion
  - marks it failed (with next_retry_at) on transient error
  - marks it dead_letter after max retries exhausted

Retry back-off: 30s → 5 min → 30 min (more operator-friendly than the
previous 5s exponential doubling).
"""
import logging
from datetime import UTC, datetime, timedelta

from celery.exceptions import MaxRetriesExceededError

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Back-off schedule per retry attempt (0-indexed)
_RETRY_COUNTDOWNS = [30, 300, 1800]


def _countdown(retry_num: int) -> int:
    return _RETRY_COUNTDOWNS[min(retry_num, len(_RETRY_COUNTDOWNS) - 1)]


def _next_retry_ts(countdown_s: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=countdown_s)).isoformat()


@celery_app.task(bind=True, max_retries=3, name="app.worker.tasks.execute_flow_task")
def execute_flow_task(
    self,
    flow_id: str,
    request_id: str,
    tenant_id: int | None,
    delivery_id: str | None = None,  # present for webhook-triggered runs only
) -> None:
    from app.services.flow_service import flow_service

    try:
        flow_service._execute_flow_sync(flow_id, request_id, tenant_id)

        # Success — resolve the delivery record if this was a webhook trigger
        if delivery_id:
            _mark_delivery_succeeded(delivery_id)

    except Exception as exc:
        countdown = _countdown(self.request.retries)
        logger.warning(
            "Flow task failed (attempt %d/%d): %s — retrying in %ds",
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
            countdown,
        )

        if delivery_id:
            _mark_delivery_failed(
                delivery_id,
                error=str(exc),
                next_retry_at=_next_retry_ts(countdown),
            )

        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error("Flow task dead-lettered after %d retries: %s", self.max_retries, exc)
            flow_service._mark_run_dead_letter(
                request_id,
                tenant_id,
                f"Execution failed after {self.max_retries} retries: {exc}",
            )
            if delivery_id:
                _mark_delivery_dead_letter(delivery_id, str(exc))


# ---------------------------------------------------------------------------
# Delivery status helpers — lazy imports prevent circular dependency
# ---------------------------------------------------------------------------


def _mark_delivery_succeeded(delivery_id: str) -> None:
    try:
        from app.services.webhook_delivery_service import webhook_delivery_service
        webhook_delivery_service.mark_succeeded(delivery_id)
    except Exception as e:
        logger.warning("Could not mark delivery succeeded delivery_id=%s: %s", delivery_id, e)


def _mark_delivery_failed(delivery_id: str, error: str, next_retry_at: str | None) -> None:
    try:
        from app.services.webhook_delivery_service import webhook_delivery_service
        webhook_delivery_service.mark_failed(
            delivery_id, error, increment_attempt=False, next_retry_at=next_retry_at
        )
    except Exception as e:
        logger.warning("Could not mark delivery failed delivery_id=%s: %s", delivery_id, e)


def _mark_delivery_dead_letter(delivery_id: str, error: str) -> None:
    try:
        from app.services.webhook_delivery_service import webhook_delivery_service
        webhook_delivery_service.mark_dead_letter(delivery_id, error)
    except Exception as e:
        logger.warning("Could not mark delivery dead_letter delivery_id=%s: %s", delivery_id, e)
