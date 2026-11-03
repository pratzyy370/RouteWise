"""Fare analytics, prediction, and alert schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.journey import LocationInput


class FareHistoryRequest(BaseModel):
    """Request for historical fare data between two points."""

    origin: LocationInput
    destination: LocationInput
    provider: str | None = Field(None, description="Filter by provider")
    vehicle_type: str | None = Field(None, description="Filter by vehicle type")
    days: int = Field(30, ge=1, le=365, description="Lookback period in days")


class FareHistoryResponse(BaseModel):
    """Aggregated fare statistics for a route over a time period."""

    provider: str
    vehicle_type: str
    route: str = Field(
        ..., description="Human-readable route description, e.g. 'Andheri → Bandra'"
    )
    period_days: int
    sample_count: int = Field(..., ge=0)
    average_fare: Decimal
    median_fare: Decimal
    min_fare: Decimal
    max_fare: Decimal
    fare_by_hour: dict[str, Decimal] | None = Field(
        None,
        description="Average fare keyed by hour-of-day (0–23)",
    )
    fare_by_day: dict[str, Decimal] | None = Field(
        None,
        description="Average fare keyed by day-of-week (Mon–Sun)",
    )
    is_demo_data: bool = Field(
        ..., description="True if the statistics are based on synthetic data"
    )
    data_sufficient: bool = Field(
        ...,
        description="True if sample_count is large enough for reliable statistics",
    )


class FarePredictionResponse(BaseModel):
    """ML/heuristic fare prediction for a future trip."""

    provider: str
    vehicle_type: str
    predicted_fare: Decimal
    predicted_min: Decimal
    predicted_max: Decimal
    prediction_timestamp: datetime
    training_period_days: int
    sample_size: int = Field(..., ge=0)
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence (0–1)"
    )
    method: str = Field(
        ...,
        description="Prediction method used",
        examples=["linear_regression", "moving_average", "heuristic", "demo"],
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Caveats or limitations of this prediction",
    )


class FareAlertCreate(BaseModel):
    """Payload to create a fare-drop alert."""

    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    origin_name: str | None = Field(None, max_length=200)
    dest_name: str | None = Field(None, max_length=200)
    provider: str | None = None
    vehicle_type: str | None = None
    target_fare: Decimal = Field(..., gt=0, description="Alert when fare drops to this")
    cooldown_minutes: int = Field(
        60, ge=5, le=1440, description="Minimum minutes between alerts"
    )


class FareAlertResponse(BaseModel):
    """Public representation of a fare alert."""

    id: UUID
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    origin_name: str | None
    dest_name: str | None
    provider: str | None
    vehicle_type: str | None
    target_fare: Decimal
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
