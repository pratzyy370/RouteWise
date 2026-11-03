"""Common shared schemas used across the RouteWise application."""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    detail: str = Field(..., description="Human-readable error description")
    error_code: str | None = Field(
        None, description="Machine-readable error code, e.g. 'AUTH_TOKEN_EXPIRED'"
    )
    request_id: str | None = Field(
        None, description="Correlation ID for tracing the request"
    )


class PaginatedResponse[T](BaseModel):
    """Generic paginated list wrapper."""

    items: list[T]
    total: int = Field(..., ge=0, description="Total number of records")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")


class HealthResponse(BaseModel):
    """Application health-check response."""

    status: str = Field(..., examples=["healthy", "degraded", "unhealthy"])
    version: str = Field(..., examples=["0.1.0"])
    uptime_seconds: float | None = Field(
        None, description="Seconds since the process started"
    )
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="Component-level health, e.g. {'database': 'ok', 'redis': 'ok'}",
    )


class ProviderStatusResponse(BaseModel):
    """Status of a single external ride-hailing / transit provider."""

    provider: str = Field(..., examples=["uber", "ola", "rapido"])
    status: str = Field(
        ...,
        description="Current provider status",
        examples=["configured", "demo", "unavailable", "error"],
    )
    demo_mode: bool = Field(
        ..., description="True when the provider is returning synthetic data"
    )
    last_check: datetime | None = Field(
        None, description="UTC timestamp of the last health probe"
    )
    message: str | None = Field(
        None, description="Optional human-readable status note"
    )
