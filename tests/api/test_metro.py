"""
API tests for metro discovery, stations, and route calculations.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_metro_stations_list(client: AsyncClient):
    response = await client.get("/api/v1/metro/stations")
    assert response.status_code == 200
    stations = response.json()
    assert len(stations) > 10
    names = [s["name"] for s in stations]
    assert any("Indiranagar" in n for n in names)
    assert any("Majestic" in n for n in names)


@pytest.mark.asyncio
async def test_metro_nearby(client: AsyncClient):
    # Search around Indiranagar (12.9784, 77.6385)
    response = await client.get("/api/v1/metro/nearby?lat=12.9784&lng=77.6385&radius_m=2000&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert len(data["stations"]) > 0
    assert data["stations"][0]["distance_m"] < 2000


@pytest.mark.asyncio
async def test_metro_route_calculation(client: AsyncClient):
    # From Indiranagar (IDN) to MG Road (MGR)
    response = await client.get("/api/v1/metro/route?from_code=IDN&to_code=MGR")
    assert response.status_code == 200
    route = response.json()
    assert route["origin_code"] == "IDN"
    assert route["dest_code"] == "MGR"
    assert route["cost"] > 0
    assert route["duration_minutes"] > 0

