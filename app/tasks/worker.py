"""
Background asynchronous tasks for fare refresh, alert evaluation, and history aggregation.
"""

import asyncio
import logging
from datetime import UTC

from app.db.session import async_session_factory
from app.services.alert_service import AlertService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Utility to run asynchronous coroutine inside a synchronous Celery worker."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.worker.evaluate_fare_alerts_task", max_retries=3, default_retry_delay=60)
def evaluate_fare_alerts_task():
    """Background task to evaluate all active fare alerts."""
    logger.info("Executing evaluate_fare_alerts_task...")

    async def _evaluate():
        async with async_session_factory() as session:
            triggered = await AlertService.evaluate_active_alerts(session)
            logger.info("Evaluated alerts. %d alerts triggered.", len(triggered))
            return len(triggered)

    try:
        return run_async(_evaluate())
    except Exception as exc:
        logger.error("Error evaluating fare alerts: %s", exc)
        raise exc


@celery_app.task(name="app.tasks.worker.aggregate_daily_fare_history_task")
def aggregate_daily_fare_history_task():
    """Background task to aggregate daily fare observations and clean up expired quotes."""
    logger.info("Executing aggregate_daily_fare_history_task...")

    async def _cleanup():
        from datetime import datetime

        from sqlalchemy import delete

        from app.models.fare import FareQuote

        async with async_session_factory() as session:
            now = datetime.now(UTC)
            # Clean up quotes expired more than 7 days ago
            stmt = delete(FareQuote).where(FareQuote.expires_at < now)
            res = await session.execute(stmt)
            await session.commit()
            logger.info("Cleaned up expired quotes.")
            return res.rowcount

    try:
        return run_async(_cleanup())
    except Exception as exc:
        logger.error("Error aggregating fare history: %s", exc)
        return 0
