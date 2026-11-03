"""
Trip logging and savings analytics endpoints.
"""

from fastapi import APIRouter, Query, status

from app.api.dependencies import CurrentUser, DbSession
from app.repositories.trip_repo import TripRepository
from app.schemas.trip import (
    CompletedTripCreate,
    CompletedTripResponse,
    SavingsResponse,
)
from app.services.savings_service import SavingsService

router = APIRouter(tags=["Trips"])


@router.post("", response_model=CompletedTripResponse, status_code=status.HTTP_201_CREATED)
async def log_completed_trip(
    payload: CompletedTripCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Log an actual completed journey and payment for commute analytics."""
    trip = await TripRepository.create_trip(
        db=db,
        user_id=current_user.id,
        data=payload.model_dump(),
    )
    await db.commit()
    await db.refresh(trip)
    return trip


@router.get("", response_model=dict)
async def list_completed_trips(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """Retrieve logged trips for the authenticated user with pagination."""
    trips, total = await TripRepository.get_user_trips(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    items = [CompletedTripResponse.model_validate(t) for t in trips]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/savings", response_model=SavingsResponse)
async def get_savings_summary(
    days: int = Query(30, ge=1, le=365, description="Period in days"),
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """
    Compute total spend, counterfactual cheapest alternatives, and potential savings.
    Includes explicit disclaimers for counterfactual estimates.
    """
    return await SavingsService.get_savings_summary(
        db=db,
        user_id=current_user.id,
        days=days,
    )
