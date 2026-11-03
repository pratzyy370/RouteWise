"""Repository for CompletedTrip persistence and spending analytics."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import CompletedTrip

logger = logging.getLogger(__name__)


class TripRepository:
    """Data-access layer for :class:`CompletedTrip` entities and spending summaries."""

    # ── Create ────────────────────────────────────────────────────────────

    @staticmethod
    async def create_trip(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> CompletedTrip:
        """Log a completed trip for *user_id*.

        ``data`` must include ``origin_lat``, ``origin_lng``, ``dest_lat``,
        ``dest_lng``, ``mode``, ``actual_cost``, ``trip_date``, and optionally
        ``origin_name``, ``dest_name``, ``provider``, ``estimated_cost``,
        ``actual_duration_minutes``.
        """
        trip = CompletedTrip(
            user_id=user_id,
            origin_lat=data["origin_lat"],
            origin_lng=data["origin_lng"],
            dest_lat=data["dest_lat"],
            dest_lng=data["dest_lng"],
            origin_name=data.get("origin_name"),
            dest_name=data.get("dest_name"),
            mode=data["mode"],
            provider=data.get("provider"),
            actual_cost=data["actual_cost"],
            estimated_cost=data.get("estimated_cost"),
            actual_duration_minutes=data.get("actual_duration_minutes"),
            trip_date=data["trip_date"],
        )
        db.add(trip)
        await db.flush()
        await db.refresh(trip)
        logger.info(
            "Created completed trip id=%s mode=%s cost=%s for user=%s",
            trip.id,
            trip.mode,
            trip.actual_cost,
            user_id,
        )
        return trip

    # ── Read (paginated) ──────────────────────────────────────────────────

    @staticmethod
    async def get_user_trips(
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CompletedTrip], int]:
        """Return a page of trips for *user_id* and the total count.

        Results are ordered by ``trip_date`` descending (most recent first).
        """
        # Total count
        count_stmt = (
            select(func.count())
            .select_from(CompletedTrip)
            .where(CompletedTrip.user_id == user_id)
        )
        total_result = await db.execute(count_stmt)
        total: int = total_result.scalar_one()

        # Page of records
        offset = (page - 1) * page_size
        data_stmt = (
            select(CompletedTrip)
            .where(CompletedTrip.user_id == user_id)
            .order_by(CompletedTrip.trip_date.desc(), CompletedTrip.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        data_result = await db.execute(data_stmt)
        trips = list(data_result.scalars().all())

        return trips, total

    # ── Spending summary ──────────────────────────────────────────────────

    @staticmethod
    async def get_spending_summary(
        db: AsyncSession,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """Compute spending analytics for *user_id* over the last *days* days.

        Returns a dictionary with:
        - ``total_spend``: sum of ``actual_cost``
        - ``total_cheapest_alternatives``: sum of ``cheapest_alternative_cost``
          (uses ``actual_cost`` as fallback when no alternative is recorded)
        - ``potential_savings``: difference
        - ``trip_count``: number of trips
        - ``period_days``: the requested window
        """
        since = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(CompletedTrip)
            .where(
                CompletedTrip.user_id == user_id,
                CompletedTrip.created_at >= since,
            )
            .order_by(CompletedTrip.trip_date.desc())
        )
        result = await db.execute(stmt)
        trips = list(result.scalars().all())

        total_spend = Decimal("0")
        total_cheapest = Decimal("0")

        for trip in trips:
            total_spend += trip.actual_cost
            # Use cheapest_alternative_cost when available; fall back to actual
            alt = trip.cheapest_alternative_cost or trip.actual_cost
            total_cheapest += alt

        potential_savings = max(total_spend - total_cheapest, Decimal("0"))

        return {
            "total_spend": total_spend,
            "total_cheapest_alternatives": total_cheapest,
            "potential_savings": potential_savings,
            "trip_count": len(trips),
            "period_days": days,
        }
