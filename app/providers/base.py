"""
Base provider abstractions for RouteWise ride services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class ProviderStatus(StrEnum):
    CONFIGURED = "configured"
    DEMO = "demo"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class QuoteSource(StrEnum):
    LIVE = "live"
    DEMO = "demo"
    CACHED = "cached"
    MODELLED = "modelled"


@dataclass
class FareEstimate:
    provider: str
    vehicle_type: str
    estimated_fare: Decimal
    fare_min: Decimal | None = None
    fare_max: Decimal | None = None
    currency: str = "INR"
    estimated_duration_minutes: float | None = None
    distance_m: float | None = None
    quote_source: QuoteSource = QuoteSource.DEMO
    surge_multiplier: float = 1.0
    booking_url: str | None = None
    quoted_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    error: str | None = None


class BaseProvider(ABC):
    """Abstract interface for all ride-hailing and transit service providers."""

    name: str
    display_name: str
    supported_vehicle_types: list[str]

    @abstractmethod
    async def get_fare_estimates(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> list[FareEstimate]:
        """Fetch quotes or estimates for the given coordinate pair."""
        ...

    @abstractmethod
    async def get_status(self) -> ProviderStatus:
        """Return provider integration status."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if live credentials are configured."""
        ...
