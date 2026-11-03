"""
Personal Commute Savings Analytics Service.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip import CompletedTrip
from app.repositories.trip_repo import TripRepository
from app.schemas.trip import SavingsResponse


class SavingsService:
    @staticmethod
    async def get_savings_summary(
        db: AsyncSession,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> SavingsResponse:
        summary = await TripRepository.get_spending_summary(db, user_id, days=days)

        # Get per-route breakdowns where user took cabs instead of cheaper alternatives
        stmt = (
            select(
                CompletedTrip.origin_name,
                CompletedTrip.dest_name,
                func.count(CompletedTrip.id).label("trip_count"),
                func.sum(CompletedTrip.actual_cost).label("total_spent"),
            )
            .where(CompletedTrip.user_id == user_id)
            .group_by(CompletedTrip.origin_name, CompletedTrip.dest_name)
            .limit(5)
        )
        res = await db.execute(stmt)
        routes_summary = []
        for orig, dst, cnt, spent in res.all():
            routes_summary.append(
                {
                    "route": f"{orig or 'Start'} → {dst or 'End'}",
                    "trips": cnt,
                    "total_spent": float(spent),
                    "recommendation": "Consider Metro / Auto multimodal combination for frequent commutes.",
                }
            )

        return SavingsResponse(
            total_spend=summary["total_spend"],
            total_cheapest_alternatives=summary["total_cheapest_alternatives"],
            potential_savings=summary["potential_savings"],
            trip_count=summary["trip_count"],
            period_days=summary["period_days"],
            routes_with_savings=routes_summary,
            savings_disclaimer=(
                "Counterfactual savings are estimates based on lowest available alternatives at search time. "
                "RouteWise does not claim guaranteed savings for unselected travel options."
            ),
        )
