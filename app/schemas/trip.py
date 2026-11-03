"""Completed-trip and spending-analysis schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CompletedTripCreate(BaseModel):
    """Payload to log a completed trip."""

    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    dest_lat: float = Field(..., ge=-90, le=90)
    dest_lng: float = Field(..., ge=-180, le=180)
    origin_name: str | None = Field(None, max_length=200)
    dest_name: str | None = Field(None, max_length=200)
    mode: str = Field(
        ..., description="Transport mode", examples=["auto", "metro", "bus", "cab"]
    )
    provider: str | None = Field(None, examples=["uber", "ola", "rapido"])
    actual_cost: Decimal = Field(..., gt=0, description="Actual fare paid")
    estimated_cost: Decimal | None = Field(
        None, gt=0, description="Original estimated fare"
    )
    actual_duration_minutes: int | None = Field(
        None, ge=0, description="Actual trip duration in minutes"
    )
    trip_date: date = Field(..., description="Date the trip was taken")


class CompletedTripResponse(BaseModel):
    """Public representation of a logged trip."""

    id: UUID
    user_id: UUID
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    origin_name: str | None
    dest_name: str | None
    mode: str
    provider: str | None
    actual_cost: Decimal
    estimated_cost: Decimal | None
    actual_duration_minutes: int | None
    trip_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class SavingsResponse(BaseModel):
    """Spending analysis and potential savings summary."""

    total_spend: Decimal = Field(..., description="Total amount spent on trips")
    total_cheapest_alternatives: Decimal = Field(
        ..., description="What those trips would have cost using cheapest options"
    )
    potential_savings: Decimal = Field(
        ..., description="Difference (total_spend − total_cheapest_alternatives)"
    )
    trip_count: int = Field(..., ge=0)
    period_days: int = Field(..., ge=1)
    routes_with_savings: list[dict] = Field(
        default_factory=list,
        description="Per-route savings breakdown",
    )
    savings_disclaimer: str = Field(
        ...,
        description="Disclaimer about accuracy of savings estimates",
    )
