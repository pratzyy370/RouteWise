"""
Demo providers for Uber, Ola, Rapido, and Namma Yatri.

All demo providers use deterministic calculations based on geographic distance,
traffic models, and realistic Bengaluru fare structures.
Every estimate is explicitly tagged as QuoteSource.DEMO.
"""

import math
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.providers.base import BaseProvider, FareEstimate, ProviderStatus, QuoteSource


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def get_road_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Road distance with urban detour factor (typically 1.25x - 1.35x in Bengaluru)."""
    return haversine_distance_km(lat1, lon1, lat2, lon2) * 1.30


def get_deterministic_factor(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Produces a deterministic float between 0.95 and 1.05 based on coordinates."""
    raw = abs(int((lat1 + lon1 + lat2 + lon2) * 10000))
    return 0.95 + ((raw % 100) / 1000.0)


class UberDemoProvider(BaseProvider):
    name = "uber"
    display_name = "Uber"
    supported_vehicle_types = ["Uber Go", "Uber Auto", "Uber Premier"]

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus.CONFIGURED if self.is_configured() else ProviderStatus.DEMO

    async def get_fare_estimates(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> list[FareEstimate]:
        dist_km = max(0.5, get_road_distance_km(origin_lat, origin_lng, dest_lat, dest_lng))
        dist_m = dist_km * 1000
        dur_mins = round(dist_km * 3.2 + 5, 1)  # ~18-20 km/h in Bengaluru
        det_var = get_deterministic_factor(origin_lat, origin_lng, dest_lat, dest_lng)
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=5)

        rates = [
            ("Uber Auto", 35.0, 15.0, "https://m.uber.com/looking"),
            ("Uber Go", 60.0, 18.0, "https://m.uber.com/looking"),
            ("Uber Premier", 90.0, 24.0, "https://m.uber.com/looking"),
        ]

        estimates = []
        for v_type, base_fare, per_km, book_url in rates:
            raw_cost = (base_fare + (dist_km * per_km)) * det_var
            cost = Decimal(str(round(raw_cost, 2))).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
            min_cost = (cost * Decimal("0.95")).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
            max_cost = (cost * Decimal("1.10")).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)

            estimates.append(
                FareEstimate(
                    provider=self.name,
                    vehicle_type=v_type,
                    estimated_fare=cost,
                    fare_min=min_cost,
                    fare_max=max_cost,
                    currency="INR",
                    estimated_duration_minutes=dur_mins,
                    distance_m=round(dist_m, 1),
                    quote_source=QuoteSource.DEMO,
                    surge_multiplier=1.0,
                    booking_url=book_url,
                    quoted_at=now,
                    expires_at=expires_at,
                )
            )
        return estimates


class OlaDemoProvider(BaseProvider):
    name = "ola"
    display_name = "Ola"
    supported_vehicle_types = ["Ola Auto", "Ola Mini", "Ola Prime"]

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus.CONFIGURED if self.is_configured() else ProviderStatus.DEMO

    async def get_fare_estimates(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> list[FareEstimate]:
        dist_km = max(0.5, get_road_distance_km(origin_lat, origin_lng, dest_lat, dest_lng))
        dist_m = dist_km * 1000
        dur_mins = round(dist_km * 3.3 + 4, 1)
        det_var = get_deterministic_factor(origin_lat + 0.1, origin_lng, dest_lat, dest_lng)
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=5)

        rates = [
            ("Ola Auto", 33.0, 14.5, "https://book.olacabs.com"),
            ("Ola Mini", 55.0, 17.5, "https://book.olacabs.com"),
            ("Ola Prime", 85.0, 23.0, "https://book.olacabs.com"),
        ]

        estimates = []
        for v_type, base_fare, per_km, book_url in rates:
            raw_cost = (base_fare + (dist_km * per_km)) * det_var
            cost = Decimal(str(round(raw_cost, 2))).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
            min_cost = (cost * Decimal("0.92")).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
            max_cost = (cost * Decimal("1.12")).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)

            estimates.append(
                FareEstimate(
                    provider=self.name,
                    vehicle_type=v_type,
                    estimated_fare=cost,
                    fare_min=min_cost,
                    fare_max=max_cost,
                    currency="INR",
                    estimated_duration_minutes=dur_mins,
                    distance_m=round(dist_m, 1),
                    quote_source=QuoteSource.DEMO,
                    surge_multiplier=1.0,
                    booking_url=book_url,
                    quoted_at=now,
                    expires_at=expires_at,
                )
            )
        return estimates


class RapidoDemoProvider(BaseProvider):
    name = "rapido"
    display_name = "Rapido"
    supported_vehicle_types = ["Rapido Bike", "Rapido Auto"]

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus.CONFIGURED if self.is_configured() else ProviderStatus.DEMO

    async def get_fare_estimates(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> list[FareEstimate]:
        dist_km = max(0.5, get_road_distance_km(origin_lat, origin_lng, dest_lat, dest_lng))
        dist_m = dist_km * 1000
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=5)
        det_var = get_deterministic_factor(origin_lat, origin_lng + 0.1, dest_lat, dest_lng)

        estimates = []

        # Bike is faster through traffic (~25 km/h)
        bike_mins = round(dist_km * 2.4 + 3, 1)
        bike_cost = Decimal(str(round((20.0 + (dist_km * 9.0)) * det_var, 2))).quantize(
            Decimal("1.00"), rounding=ROUND_HALF_UP
        )
        estimates.append(
            FareEstimate(
                provider=self.name,
                vehicle_type="Rapido Bike",
                estimated_fare=bike_cost,
                fare_min=(bike_cost * Decimal("0.95")).quantize(Decimal("1.00")),
                fare_max=(bike_cost * Decimal("1.05")).quantize(Decimal("1.00")),
                currency="INR",
                estimated_duration_minutes=bike_mins,
                distance_m=round(dist_m, 1),
                quote_source=QuoteSource.DEMO,
                booking_url="https://rapido.bike",
                quoted_at=now,
                expires_at=expires_at,
            )
        )

        # Auto
        auto_mins = round(dist_km * 3.2 + 4, 1)
        auto_cost = Decimal(str(round((32.0 + (dist_km * 14.0)) * det_var, 2))).quantize(
            Decimal("1.00"), rounding=ROUND_HALF_UP
        )
        estimates.append(
            FareEstimate(
                provider=self.name,
                vehicle_type="Rapido Auto",
                estimated_fare=auto_cost,
                fare_min=(auto_cost * Decimal("0.95")).quantize(Decimal("1.00")),
                fare_max=(auto_cost * Decimal("1.08")).quantize(Decimal("1.00")),
                currency="INR",
                estimated_duration_minutes=auto_mins,
                distance_m=round(dist_m, 1),
                quote_source=QuoteSource.DEMO,
                booking_url="https://rapido.bike",
                quoted_at=now,
                expires_at=expires_at,
            )
        )
        return estimates


class NammaYatriDemoProvider(BaseProvider):
    name = "namma_yatri"
    display_name = "Namma Yatri"
    supported_vehicle_types = ["Namma Yatri Auto", "Namma Yatri Cab"]

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus.CONFIGURED if self.is_configured() else ProviderStatus.DEMO

    async def get_fare_estimates(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
    ) -> list[FareEstimate]:
        dist_km = max(0.5, get_road_distance_km(origin_lat, origin_lng, dest_lat, dest_lng))
        dist_m = dist_km * 1000
        dur_mins = round(dist_km * 3.1 + 4, 1)
        det_var = get_deterministic_factor(origin_lat - 0.1, origin_lng, dest_lat, dest_lng)
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=5)

        # Namma Yatri features standard government-aligned meter/fixed rates + small driver tip
        auto_cost = Decimal(str(round((30.0 + (dist_km * 13.5)) * det_var, 2))).quantize(
            Decimal("1.00"), rounding=ROUND_HALF_UP
        )
        cab_cost = Decimal(str(round((50.0 + (dist_km * 16.0)) * det_var, 2))).quantize(
            Decimal("1.00"), rounding=ROUND_HALF_UP
        )

        return [
            FareEstimate(
                provider=self.name,
                vehicle_type="Namma Yatri Auto",
                estimated_fare=auto_cost,
                fare_min=auto_cost,
                fare_max=(auto_cost * Decimal("1.05")).quantize(Decimal("1.00")),
                currency="INR",
                estimated_duration_minutes=dur_mins,
                distance_m=round(dist_m, 1),
                quote_source=QuoteSource.DEMO,
                booking_url="https://nammayatri.in",
                quoted_at=now,
                expires_at=expires_at,
            ),
            FareEstimate(
                provider=self.name,
                vehicle_type="Namma Yatri Cab",
                estimated_fare=cab_cost,
                fare_min=cab_cost,
                fare_max=(cab_cost * Decimal("1.08")).quantize(Decimal("1.00")),
                currency="INR",
                estimated_duration_minutes=dur_mins,
                distance_m=round(dist_m, 1),
                quote_source=QuoteSource.DEMO,
                booking_url="https://nammayatri.in",
                quoted_at=now,
                expires_at=expires_at,
            ),
        ]
