"""Metro station schemas for nearby-station lookups and line queries."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class MetroStationResponse(BaseModel):
    """Public representation of a single metro station."""

    id: UUID
    name: str
    code: str
    line: str
    latitude: float
    longitude: float
    is_interchange: bool
    station_order: int
    distance_m: float | None = Field(
        None,
        ge=0,
        description="Distance from the search point in metres (populated in nearby queries)",
    )

    model_config = {"from_attributes": True}


class NearbyStationsRequest(BaseModel):
    """Query parameters for a nearby-station search."""

    lat: float = Field(..., ge=-90, le=90, description="Search latitude")
    lng: float = Field(..., ge=-180, le=180, description="Search longitude")
    radius_m: int = Field(
        1500, ge=100, le=10000, description="Search radius in metres"
    )
    limit: int = Field(5, ge=1, le=50, description="Maximum results to return")


class NearbyStationsResponse(BaseModel):
    """Response containing nearby metro stations and search metadata."""

    stations: list[MetroStationResponse]
    search_lat: float
    search_lng: float
    search_radius_m: int
    count: int = Field(..., ge=0, description="Number of stations returned")
