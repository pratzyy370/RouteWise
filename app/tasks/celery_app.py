"""
Celery background worker application configuration.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "routewise",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    beat_schedule={
        "evaluate-fare-alerts-hourly": {
            "task": "app.tasks.worker.evaluate_fare_alerts_task",
            "schedule": 3600.0,
        },
        "aggregate-fare-history-daily": {
            "task": "app.tasks.worker.aggregate_daily_fare_history_task",
            "schedule": 86400.0,
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks.worker"])
