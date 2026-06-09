import os

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "ai_integration_cloud",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["app.worker.tasks", "app.worker.beat_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true",
    beat_schedule={
        "check-scheduled-flows": {
            "task": "app.worker.beat_tasks.check_scheduled_flows",
            "schedule": 60.0,  # every 60 seconds
        },
        "expire-stuck-runs": {
            "task": "app.worker.beat_tasks.expire_stuck_runs",
            "schedule": 300.0,  # every 5 minutes
        },
    },
    beat_schedule_filename="/tmp/celerybeat-schedule",
)
