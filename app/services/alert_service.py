"""
Fare Alert Management and Evaluation Service.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fare import FareAlert
from app.repositories.fare_repo import FareRepository
from app.schemas.fare import FareAlertCreate
from app.services.fare_service import FareComparisonService

logger = logging.getLogger(__name__)


class AlertService:
    @staticmethod
    async def create_alert(
        db: AsyncSession,
        user_id: uuid.UUID,
        alert_data: FareAlertCreate,
    ) -> FareAlert:
        data_dict = alert_data.model_dump()
        return await FareRepository.create_alert(db, user_id, data_dict)

    @staticmethod
    async def get_user_alerts(db: AsyncSession, user_id: uuid.UUID) -> list[FareAlert]:
        return await FareRepository.get_alerts_for_user(db, user_id)

    @staticmethod
    async def update_alert(
        db: AsyncSession,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: dict,
    ) -> FareAlert | None:
        return await FareRepository.update_alert(db, alert_id, update_data, user_id=user_id)

    @staticmethod
    async def delete_alert(
        db: AsyncSession,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        return await FareRepository.delete_alert(db, alert_id, user_id=user_id)

    @staticmethod
    async def evaluate_active_alerts(db: AsyncSession) -> list[dict]:
        """Check all active alerts against current quotes and trigger if conditions are met."""
        active_alerts = await FareRepository.get_active_alerts(db)
        fare_service = FareComparisonService()
        now = datetime.now(UTC)
        triggered_alerts = []

        for alert in active_alerts:
            # Check cooldown
            if alert.last_triggered_at is not None:
                elapsed = (now - alert.last_triggered_at).total_seconds() / 60.0
                if elapsed < alert.cooldown_minutes:
                    continue

            # Query current fares for this alert's route
            res = await fare_service.compare_fares(
                alert.origin_lat, alert.origin_lng, alert.dest_lat, alert.dest_lng
            )
            quotes = res["quotes"]

            for q in quotes:
                matches_provider = not alert.provider or q.provider.lower() == alert.provider.lower()
                matches_vehicle = not alert.vehicle_type or q.vehicle_type.lower() == alert.vehicle_type.lower()

                if matches_provider and matches_vehicle and q.estimated_fare <= alert.target_fare:
                    # Trigger notification (development log)
                    logger.info(
                        "[DEMO NOTIFICATION] Fare alert %s triggered for user %s: %s %s fare is ₹%s (target was ₹%s)",
                        alert.id,
                        alert.user_id,
                        q.provider,
                        q.vehicle_type,
                        q.estimated_fare,
                        alert.target_fare,
                    )
                    await FareRepository.update_alert(
                        db, alert.id, {"last_triggered_at": now}
                    )
                    triggered_alerts.append(
                        {
                            "alert_id": alert.id,
                            "user_id": alert.user_id,
                            "provider": q.provider,
                            "vehicle_type": q.vehicle_type,
                            "current_fare": q.estimated_fare,
                            "target_fare": alert.target_fare,
                            "triggered_at": now.isoformat(),
                        }
                    )
                    break

        await db.commit()
        return triggered_alerts
