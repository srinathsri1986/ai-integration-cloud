"""
Celery Beat tasks — periodic background work.

check_scheduled_flows runs every 60 seconds and fires execute_flow_task for
any published flow whose cron expression matches the current minute and has
not already been triggered this minute.
"""
import logging
from datetime import UTC, datetime
from uuid import uuid4

from croniter import croniter

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.worker.beat_tasks.check_scheduled_flows")
def check_scheduled_flows() -> None:
    from app.core.database import SessionLocal
    from app.repositories.flow_definition_repository import FlowDefinitionRepository
    from app.worker.tasks import execute_flow_task

    now = datetime.now(UTC)
    logger.debug("Beat: checking scheduled flows at %s", now.isoformat())

    with SessionLocal() as session:
        specs = FlowDefinitionRepository(session).list_scheduled_flow_specs()

    fired = 0
    for spec in specs:
        cron_expr = spec["trigger_cron"]
        flow_id = spec["flow_id"]
        tenant_id = spec["tenant_id"]
        last_run_at = spec["last_run_at"]

        try:
            if not croniter.is_valid(cron_expr):
                logger.warning("Invalid cron on flow %s: %s", flow_id, cron_expr)
                continue

            cron = croniter(cron_expr, now)
            # Most recent past scheduled tick
            prev_tick: datetime = cron.get_prev(datetime)

            # Fired if the tick was within the last 60 s (this Beat interval)
            seconds_since_tick = (now - prev_tick).total_seconds()
            if seconds_since_tick > 60:
                continue

            # Don't double-fire if we already ran after this tick
            if last_run_at:
                try:
                    last_dt = datetime.fromisoformat(last_run_at)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=UTC)
                    if last_dt >= prev_tick:
                        continue
                except ValueError:
                    pass

            request_id = str(uuid4())
            logger.info(
                "Beat: firing scheduled flow %s (cron=%s, tenant=%s, request=%s)",
                flow_id, cron_expr, tenant_id, request_id,
            )

            # Create the running record then dispatch
            from app.core.database import SessionLocal as _SL
            from app.repositories.flow_run_repository import FlowRunRepository

            started = datetime.now(UTC).isoformat()
            with _SL() as session:
                FlowRunRepository(session, tenant_id).create_running(flow_id, request_id, started)

            execute_flow_task.delay(flow_id, request_id, tenant_id)
            fired += 1

        except Exception as exc:
            logger.error("Beat: error checking flow %s: %s", flow_id, exc)

    if fired:
        logger.info("Beat: fired %d scheduled flow(s)", fired)
