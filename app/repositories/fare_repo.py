"""Repository for FareQuote, FareObservation, and FareAlert operations."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fare import FareAlert, FareObservation, FareQuote

logger = logging.getLogger(__name__)

# Proximity threshold in degrees (~1 km ≈ 0.009° latitude).
_COORD_TOLERANCE = 0.01


class FareRepository:
    """Data-access layer for fare quotes, historical observations, and alerts."""

    # ── FareQuote ─────────────────────────────────────────────────────────

    @staticmethod
    async def save_quote(
        db: AsyncSession,
        quote_data: dict[str, Any],
    ) -> FareQuote:
        """Persist a fare quote snapshot.

        ``quote_data`` must include ``provider``, ``vehicle_type``,
        coordinate fields, ``estimated_fare``, ``quote_source``,
        ``quote_status``, ``quoted_at``, ``expires_at``, and optionally
        ``fare_min``, ``fare_max``, ``currency``, ``estimated_duration_minutes``,
        ``distance_m``, ``surge_multiplier``, ``booking_url``.
        """
        quote = FareQuote(
            provider=quote_data["provider"],
            vehicle_type=quote_data["vehicle_type"],
            origin_lat=quote_data["origin_lat"],
            origin_lng=quote_data["origin_lng"],
            dest_lat=quote_data["dest_lat"],
            dest_lng=quote_data["dest_lng"],
            estimated_fare=quote_data["estimated_fare"],
            fare_min=quote_data.get("fare_min"),
            fare_max=quote_data.get("fare_max"),
            currency=quote_data.get("currency", "INR"),
            estimated_duration_minutes=quote_data.get("estimated_duration_minutes"),
            distance_m=quote_data.get("distance_m"),
            quote_source=quote_data.get("quote_source", "demo"),
            quote_status=quote_data.get("quote_status", "active"),
            surge_multiplier=quote_data.get("surge_multiplier"),
            booking_url=quote_data.get("booking_url"),
            quoted_at=quote_data["quoted_at"],
            expires_at=quote_data["expires_at"],
        )
        db.add(quote)
        await db.flush()
        await db.refresh(quote)
        logger.info(
            "Saved fare quote id=%s provider=%s fare=%s",
            quote.id,
            quote.provider,
            quote.estimated_fare,
        )
        return quote

    # ── FareObservation ───────────────────────────────────────────────────

    @staticmethod
    async def save_observation(
        db: AsyncSession,
        obs_data: dict[str, Any],
    ) -> FareObservation:
        """Insert a single fare observation record.

        ``obs_data`` must include ``provider``, ``vehicle_type``,
        coordinate fields, ``observed_fare``, and optionally ``currency``,
        ``is_demo_data``, ``hour_of_day``, ``day_of_week``, ``observed_at``.
        """
        obs = FareObservation(
            provider=obs_data["provider"],
            vehicle_type=obs_data["vehicle_type"],
            origin_lat=obs_data["origin_lat"],
            origin_lng=obs_data["origin_lng"],
            dest_lat=obs_data["dest_lat"],
            dest_lng=obs_data["dest_lng"],
            observed_fare=obs_data["observed_fare"],
            currency=obs_data.get("currency", "INR"),
            is_demo_data=obs_data.get("is_demo_data", True),
            hour_of_day=obs_data.get("hour_of_day"),
            day_of_week=obs_data.get("day_of_week"),
            observed_at=obs_data.get("observed_at", datetime.now(UTC)),
        )
        db.add(obs)
        await db.flush()
        await db.refresh(obs)
        logger.debug(
            "Saved fare observation id=%s provider=%s fare=%s",
            obs.id,
            obs.provider,
            obs.observed_fare,
        )
        return obs

    @staticmethod
    async def get_observations(
        db: AsyncSession,
        *,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        provider: str | None = None,
        vehicle_type: str | None = None,
        days: int = 30,
    ) -> list[FareObservation]:
        """Retrieve fare observations matching the given filters.

        Coordinates are matched with a small tolerance (≈1 km) so that
        nearby origin/destination pairs are grouped together.
        """
        since = datetime.now(UTC) - timedelta(days=days)

        conditions = [
            FareObservation.observed_at >= since,
            FareObservation.origin_lat.between(
                origin_lat - _COORD_TOLERANCE, origin_lat + _COORD_TOLERANCE
            ),
            FareObservation.origin_lng.between(
                origin_lng - _COORD_TOLERANCE, origin_lng + _COORD_TOLERANCE
            ),
            FareObservation.dest_lat.between(
                dest_lat - _COORD_TOLERANCE, dest_lat + _COORD_TOLERANCE
            ),
            FareObservation.dest_lng.between(
                dest_lng - _COORD_TOLERANCE, dest_lng + _COORD_TOLERANCE
            ),
        ]

        if provider is not None:
            conditions.append(FareObservation.provider == provider)
        if vehicle_type is not None:
            conditions.append(FareObservation.vehicle_type == vehicle_type)

        stmt = (
            select(FareObservation)
            .where(and_(*conditions))
            .order_by(FareObservation.observed_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ── FareAlert ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_alerts_for_user(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[FareAlert]:
        """Return all fare alerts belonging to *user_id*, newest first."""
        stmt = (
            select(FareAlert)
            .where(FareAlert.user_id == user_id)
            .order_by(FareAlert.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_alert(
        db: AsyncSession,
        user_id: uuid.UUID,
        alert_data: dict[str, Any],
    ) -> FareAlert:
        """Create a new fare alert for *user_id*.

        ``alert_data`` must include ``origin_lat``, ``origin_lng``,
        ``dest_lat``, ``dest_lng``, ``target_fare``, and optionally
        ``origin_name``, ``dest_name``, ``provider``, ``vehicle_type``,
        ``cooldown_minutes``.
        """
        alert = FareAlert(
            user_id=user_id,
            origin_lat=alert_data["origin_lat"],
            origin_lng=alert_data["origin_lng"],
            dest_lat=alert_data["dest_lat"],
            dest_lng=alert_data["dest_lng"],
            origin_name=alert_data.get("origin_name"),
            dest_name=alert_data.get("dest_name"),
            provider=alert_data.get("provider"),
            vehicle_type=alert_data.get("vehicle_type"),
            target_fare=alert_data["target_fare"],
            is_active=True,
            cooldown_minutes=alert_data.get("cooldown_minutes", 60),
        )
        db.add(alert)
        await db.flush()
        await db.refresh(alert)
        logger.info(
            "Created fare alert id=%s target=₹%s for user=%s",
            alert.id,
            alert.target_fare,
            user_id,
        )
        return alert

    @staticmethod
    async def update_alert(
        db: AsyncSession,
        alert_id: uuid.UUID,
        data: dict[str, Any],
        *,
        user_id: uuid.UUID | None = None,
    ) -> FareAlert | None:
        """Update a fare alert.

        When *user_id* is given, ownership is enforced.
        Returns the updated alert, or ``None`` if not found / not owned.
        """
        conditions = [FareAlert.id == alert_id]
        if user_id is not None:
            conditions.append(FareAlert.user_id == user_id)

        stmt = select(FareAlert).where(and_(*conditions))
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert is None:
            return None

        allowed_fields = {
            "target_fare",
            "is_active",
            "cooldown_minutes",
            "provider",
            "vehicle_type",
            "origin_name",
            "dest_name",
            "last_triggered_at",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(alert, key, value)

        await db.flush()
        await db.refresh(alert)
        logger.info("Updated fare alert id=%s fields=%s", alert_id, list(data.keys()))
        return alert

    @staticmethod
    async def delete_alert(
        db: AsyncSession,
        alert_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> bool:
        """Delete a fare alert.

        When *user_id* is given, ownership is enforced.
        Returns ``True`` if the alert was deleted, ``False`` otherwise.
        """
        conditions = [FareAlert.id == alert_id]
        if user_id is not None:
            conditions.append(FareAlert.user_id == user_id)

        stmt = select(FareAlert).where(and_(*conditions))
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if alert is None:
            return False

        await db.delete(alert)
        await db.flush()
        logger.info("Deleted fare alert id=%s", alert_id)
        return True

    @staticmethod
    async def get_active_alerts(db: AsyncSession) -> list[FareAlert]:
        """Return all currently active fare alerts (across all users).

        Used by background workers to check for triggered alerts.
        """
        stmt = (
            select(FareAlert)
            .where(FareAlert.is_active.is_(True))
            .order_by(FareAlert.created_at)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
