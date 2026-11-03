"""
Fare history, predictive modeling, and alert endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.fare import (
    FareAlertCreate,
    FareAlertResponse,
    FareHistoryRequest,
    FareHistoryResponse,
    FarePredictionResponse,
)
from app.schemas.journey import LocationInput
from app.services.alert_service import AlertService
from app.services.fare_analytics_service import FareAnalyticsService

router = APIRouter(tags=["Fares"])


@router.post("/history", response_model=FareHistoryResponse)
async def get_fare_history(payload: FareHistoryRequest, db: DbSession):
    """
    Retrieve historical fare observations, time-of-day distributions, and aggregate statistics.
    Explicitly indicates whether results are derived from demo or market observations.
    """
    return await FareAnalyticsService.get_fare_history(
        db=db,
        origin=payload.origin,
        destination=payload.destination,
        provider=payload.provider,
        vehicle_type=payload.vehicle_type,
        days=payload.days,
    )


@router.post("/predict", response_model=FarePredictionResponse)
async def predict_fare(
    origin: LocationInput,
    destination: LocationInput,
    provider: str = Query("uber", description="Provider to predict for"),
    vehicle_type: str = Query("Uber Go", description="Vehicle type to predict for"),
    db: DbSession = None,
):
    """
    Generate transparent baseline fare predictions with confidence bounds and limitations.
    Uses historical observation samples and distance heuristics when data is sparse.
    """
    return await FareAnalyticsService.predict_fare(
        db=db,
        origin=origin,
        destination=destination,
        provider=provider,
        vehicle_type=vehicle_type,
    )


@router.get("/alerts", response_model=list[FareAlertResponse])
async def list_alerts(current_user: CurrentUser, db: DbSession):
    """List all active and paused fare alerts for the authenticated user."""
    return await AlertService.get_user_alerts(db, current_user.id)


@router.post("/alerts", response_model=FareAlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(payload: FareAlertCreate, current_user: CurrentUser, db: DbSession):
    """Create a price-drop alert for a specific route and target fare."""
    alert = await AlertService.create_alert(db, current_user.id, payload)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.patch("/alerts/{alert_id}", response_model=FareAlertResponse)
async def update_alert(
    alert_id: UUID,
    payload: dict,
    current_user: CurrentUser,
    db: DbSession,
):
    """Update target price, cooldown period, or active status of a fare alert."""
    updated = await AlertService.update_alert(db, alert_id, current_user.id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or does not belong to you",
        )
    await db.commit()
    return updated


@router.delete("/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Delete a fare alert."""
    deleted = await AlertService.delete_alert(db, alert_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or does not belong to you",
        )
    await db.commit()
    return None
