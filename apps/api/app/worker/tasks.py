import logging

from celery.exceptions import MaxRetriesExceededError

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="app.worker.tasks.execute_flow_task")
def execute_flow_task(self, flow_id: str, request_id: str, tenant_id: int | None) -> None:
    from app.services.flow_service import flow_service

    try:
        flow_service._execute_flow_sync(flow_id, request_id, tenant_id)
    except Exception as exc:
        countdown = 5 * (2 ** self.request.retries)
        logger.warning(
            "Flow task failed (attempt %d/%d): %s — retrying in %ds",
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
            countdown,
        )
        try:
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            logger.error("Flow task dead-lettered after %d retries: %s", self.max_retries, exc)
            flow_service._mark_run_dead_letter(
                request_id, tenant_id, f"Execution failed after {self.max_retries} retries: {exc}"
            )
