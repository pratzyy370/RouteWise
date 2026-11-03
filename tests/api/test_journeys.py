"""
API tests for journey comparison and multimodal optimization endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compare_fares(client: AsyncClient):
    payload = {
        "origin": {"latitude": 12.9784, "longitude": 77.6385, "address": "Indiranagar"},
        "destination": {"latitude": 12.9756, "longitude": 77.6066, "address": "MG Road"},
        "preference": "balanced",
    }
    response = await client.post("/api/v1/journeys/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "quotes" in data
    assert len(data["quotes"]) > 0
    assert "provider_status" in data
    assert data["quotes"][0]["quote_source"] == "demo"


@pytest.mark.asyncio
async def test_optimize_journey_multimodal(client: AsyncClient):
    payload = {
        "origin": {"latitude": 12.9784, "longitude": 77.6385, "address": "Indiranagar"},
        "destination": {"latitude": 12.9756, "longitude": 77.6066, "address": "MG Road"},
        "preference": "balanced",
        "include_metro": True,
        "max_walking_m": 1500,
    }
    response = await client.post("/api/v1/journeys/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommended" in data
    rec = data["recommended"]
    assert rec["is_recommended"] is True
    assert float(rec["total_cost"]) > 0
    assert len(rec["legs"]) >= 1
    assert rec["recommendation_reason"] is not None
    assert "alternatives" in data
    assert len(data["alternatives"]) >= 1
