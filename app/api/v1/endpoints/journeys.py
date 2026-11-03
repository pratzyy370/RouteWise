"""
Journey comparison and optimization endpoints.
"""

from fastapi import APIRouter

from app.api.dependencies import DbSession, OptionalUser
from app.schemas.journey import (
    CompareResponse,
    JourneyCompareRequest,
    OptimizeRequest,
)
from app.services.fare_service import FareComparisonService
from app.services.journey_service import JourneyOptimizationService

router = APIRouter(tags=["Journeys"])


@router.post("/compare")
async def compare_fares(
    payload: JourneyCompareRequest,
    db: DbSession,
    current_user: OptionalUser,
):
    """
    Compare ride-hailing fares across Uber, Ola, Rapido, and Namma Yatri.
    Requests quotes concurrently with per-provider timeouts, normalizes prices,
    and returns quotes sorted by estimated fare with freshness provenance.
    """
    fare_service = FareComparisonService()
    result = await fare_service.compare_fares(
        origin_lat=payload.origin.latitude,
        origin_lng=payload.origin.longitude,
        dest_lat=payload.destination.latitude,
        dest_lng=payload.destination.longitude,
        db=db,
    )
    return result


@router.post("/optimize", response_model=CompareResponse)
async def optimize_journey(
    payload: OptimizeRequest,
    db: DbSession,
    current_user: OptionalUser,
):
    """
    Find and optimize multimodal journeys combining walking, metro, auto, and cab.
    Ranks options according to objective preferences (cheapest, fastest, balanced),
    normalizes scoring dimensions, and synthesizes clear, human-readable explanations.
    """
    journey_service = JourneyOptimizationService()
    user_id = current_user.id if current_user else None

    return await journey_service.optimize_journey(
        origin=payload.origin,
        destination=payload.destination,
        preference=payload.preference,
        include_metro=payload.include_metro,
        max_walking_m=payload.max_walking_m,
        user_id=user_id,
        db=db,
    )
