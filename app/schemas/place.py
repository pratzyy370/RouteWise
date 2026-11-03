"""Saved-place schemas for user-bookmarked locations."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PlaceCreate(BaseModel):
    """Payload to create a new saved place."""

    name: str = Field(..., min_length=1, max_length=200, description="Place name")
    label: Literal["home", "work", "college", "other"] = Field(
        ..., description="Category label"
    )
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str | None = Field(None, max_length=500)


class PlaceUpdate(BaseModel):
    """Partial-update payload for a saved place."""

    name: str | None = Field(None, min_length=1, max_length=200)
    label: Literal["home", "work", "college", "other"] | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    address: str | None = Field(None, max_length=500)


class PlaceResponse(BaseModel):
    """Public representation of a saved place."""

    id: UUID
    name: str
    label: str
    latitude: float
    longitude: float
    address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
