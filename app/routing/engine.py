"""
Routing engine abstraction and implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.providers.demo_providers import get_road_distance_km, haversine_distance_km


@dataclass
class RouteResult:
    distance_m: float
    duration_minutes: float
    source: str
    geometry: list[tuple[float, float]] | None = None


class RoutingEngine(ABC):
    @abstractmethod
    async def get_route(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: str = "driving"
    ) -> RouteResult:
        """Calculate route distance and estimated duration."""
        ...


class DemoRoutingEngine(RoutingEngine):
    """
    Deterministic urban routing model based on realistic Bengaluru traffic velocities:
    - Walking: ~4.5 km/h
    - Auto / Cab: ~18 km/h
    - Bike: ~24 km/h
    - Metro: ~36 km/h
    """

    async def get_route(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: str = "driving"
    ) -> RouteResult:
        if mode == "walking":
            dist_km = haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng) * 1.15
            duration_mins = (dist_km / 4.5) * 60
        elif mode == "metro":
            dist_km = haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
            duration_mins = (dist_km / 36.0) * 60 + 3.0  # +3 min wait/dwell
        elif mode == "bike":
            dist_km = get_road_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
            duration_mins = (dist_km / 24.0) * 60
        else:  # driving / auto / cab
            dist_km = get_road_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
            duration_mins = (dist_km / 18.5) * 60 + 4.0  # signals + pickup

        return RouteResult(
            distance_m=round(dist_km * 1000, 1),
            duration_minutes=round(max(1.0, duration_mins), 1),
            source="demo",
            geometry=[(origin_lat, origin_lng), (dest_lat, dest_lng)],
        )


class OSRMRoutingEngine(RoutingEngine):
    """Routing engine querying an OSRM instance with graceful fallback."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.fallback = DemoRoutingEngine()

    async def get_route(
        self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: str = "driving"
    ) -> RouteResult:
        osrm_profile = "foot" if mode == "walking" else "driving"
        url = f"{self.base_url}/route/v1/{osrm_profile}/{origin_lng},{origin_lat};{dest_lng},{dest_lat}?overview=simplified"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    routes = data.get("routes", [])
                    if routes:
                        r0 = routes[0]
                        return RouteResult(
                            distance_m=float(r0["distance"]),
                            duration_minutes=round(float(r0["duration"]) / 60.0, 1),
                            source="osrm",
                        )
        except Exception:
            pass  # Fall back on connection error, timeout, or invalid response
        return await self.fallback.get_route(origin_lat, origin_lng, dest_lat, dest_lng, mode)


_routing_engine_instance: RoutingEngine | None = None


def get_routing_engine() -> RoutingEngine:
    global _routing_engine_instance
    if _routing_engine_instance is None:
        settings = get_settings()
        if settings.ROUTING_ENGINE_URL:
            _routing_engine_instance = OSRMRoutingEngine(settings.ROUTING_ENGINE_URL)
        else:
            _routing_engine_instance = DemoRoutingEngine()
    return _routing_engine_instance
