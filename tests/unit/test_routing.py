"""
Unit tests for geodesic calculations and demo routing engine.
"""

import pytest

from app.providers.demo_providers import get_road_distance_km, haversine_distance_km
from app.routing.engine import DemoRoutingEngine


def test_haversine_distance():
    # Indiranagar (12.9784, 77.6385) to MG Road (12.9756, 77.6066) is ~3.5 km
    dist = haversine_distance_km(12.9784, 77.6385, 12.9756, 77.6066)
    assert 3.0 < dist < 4.0


def test_road_distance_detour():
    h_dist = haversine_distance_km(12.9784, 77.6385, 12.9756, 77.6066)
    r_dist = get_road_distance_km(12.9784, 77.6385, 12.9756, 77.6066)
    assert r_dist > h_dist
    assert r_dist == pytest.approx(h_dist * 1.30, rel=1e-3)


@pytest.mark.asyncio
async def test_demo_routing_engine():
    engine = DemoRoutingEngine()
    route = await engine.get_route(12.9784, 77.6385, 12.9756, 77.6066, mode="driving")
    assert route.distance_m > 3000
    assert route.duration_minutes > 5
    assert route.source == "demo"
