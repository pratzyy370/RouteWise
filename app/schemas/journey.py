"""Journey planning, comparison, and optimization schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class LocationInput(BaseModel):
    """A geographical point with optional human-readable address."""

    latitude: float = Field(..., ge=-90, le=90, description="WGS-84 latitude")
    longitude: float = Field(..., ge=-180, le=180, description="WGS-84 longitude")
    address: str | None = Field(None, max_length=500, description="Optional address text")


class JourneyCompareRequest(BaseModel):
    """Request to compare journey options between two locations."""

    origin: LocationInput
    destination: LocationInput
    preference: Literal["cheapest", "fastest", "balanced"] = Field(
        "balanced",
        description="Optimisation preference for ranking results",
    )


class FareQuoteResponse(BaseModel):
    """A single fare quote from a ride-hailing or transit provider."""

    provider: str = Field(..., examples=["uber", "ola", "rapido"])
    vehicle_type: str = Field(..., examples=["auto", "mini", "sedan"])
    estimated_fare: Decimal = Field(..., description="Best-estimate fare")
    fare_min: Decimal | None = Field(None, description="Lower bound of fare range")
    fare_max: Decimal | None = Field(None, description="Upper bound of fare range")
    currency: str = Field("INR", max_length=3)
    estimated_duration_minutes: float | None = Field(
        None, ge=0, description="Estimated travel time in minutes"
    )
    distance_m: float | None = Field(None, ge=0, description="Distance in metres")
    quote_source: str = Field(
        ...,
        description="How the quote was obtained",
        examples=["api", "scrape", "estimate", "demo"],
    )
    quote_status: str = Field(
        ...,
        description="Freshness / reliability of the quote",
        examples=["live", "cached", "estimated", "demo"],
    )
    surge_multiplier: float | None = Field(
        None, ge=1.0, description="Surge / dynamic pricing multiplier"
    )
    booking_url: str | None = Field(
        None, description="Deep-link to complete the booking"
    )
    quoted_at: datetime = Field(..., description="When the quote was generated (UTC)")
    expires_at: datetime = Field(..., description="When the quote expires (UTC)")

    @computed_field  # type: ignore[misc]
    @property
    def is_expired(self) -> bool:
        """Whether this quote has passed its expiry timestamp."""

        return datetime.now(UTC) > self.expires_at.replace(
            tzinfo=self.expires_at.tzinfo or UTC
        )


class JourneyLegResponse(BaseModel):
    """A single leg (segment) of a multi-modal journey."""

    leg_order: int = Field(..., ge=0, description="0-indexed position in the journey")
    mode: str = Field(
        ..., description="Transport mode", examples=["walk", "auto", "metro", "bus"]
    )
    origin_lat: float
    origin_lng: float
    origin_name: str | None = None
    dest_lat: float
    dest_lng: float
    dest_name: str | None = None
    estimated_cost: Decimal = Field(..., description="Cost for this leg")
    estimated_duration_minutes: float = Field(..., ge=0)
    distance_m: float = Field(..., ge=0)
    provider: str | None = Field(
        None, description="Provider name for ride-hailing legs"
    )
    data_source: str = Field(
        ...,
        description="Where the data came from",
        examples=["live_api", "cached", "estimated", "demo"],
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this leg's estimates (0–1)",
    )


class JourneyOptionResponse(BaseModel):
    """A fully-resolved journey option (may have multiple legs)."""

    id: UUID
    rank: int = Field(..., ge=1, description="1-indexed rank within the search")
    is_recommended: bool
    total_cost: Decimal
    total_duration_minutes: float = Field(..., ge=0)
    total_distance_m: float = Field(..., ge=0)
    walking_distance_m: float = Field(0, ge=0)
    transfer_count: int = Field(0, ge=0)
    score: float = Field(
        ..., ge=0.0, description="Composite ranking score (higher is better)"
    )
    recommendation_reason: str | None = Field(
        None, description="Why this option was recommended"
    )
    legs: list[JourneyLegResponse]
    data_freshness: dict[str, str] = Field(
        default_factory=dict,
        description="Per-source freshness info, e.g. {'uber': 'live', 'metro': 'static'}",
    )


class CompareResponse(BaseModel):
    """Top-level response for a journey comparison request."""

    search_id: UUID
    recommended: JourneyOptionResponse
    alternatives: list[JourneyOptionResponse]
    provider_status: dict[str, str] = Field(
        default_factory=dict,
        description="Status of each provider queried, e.g. {'uber': 'ok', 'ola': 'demo'}",
    )
    data_disclaimer: str = Field(
        ...,
        description="Legal / accuracy disclaimer shown to end users",
    )


class OptimizeRequest(BaseModel):
    """Request for an optimised multi-modal route suggestion."""

    origin: LocationInput
    destination: LocationInput
    preference: Literal["cheapest", "fastest", "balanced"] = "balanced"
    include_metro: bool = Field(
        True, description="Whether to consider metro in suggestions"
    )
    max_walking_m: int = Field(
        1500,
        ge=0,
        le=5000,
        description="Maximum acceptable walking distance in metres",
    )
