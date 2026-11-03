"""
API tests for completed trip logging and commute savings analytics.
"""

import pytest
from httpx import AsyncClient


async def get_user_token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "User"},
    )
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_trip_logging_and_savings(client: AsyncClient):
    token = await get_user_token(client, "tripper@example.com")

    # 1. Log a completed trip
    payload = {
        "origin_lat": 12.9784,
        "origin_lng": 77.6385,
        "dest_lat": 12.9756,
        "dest_lng": 77.6066,
        "origin_name": "Indiranagar",
        "dest_name": "MG Road",
        "mode": "cab",
        "provider": "uber",
        "actual_cost": 150.0,
        "trip_date": "2026-11-01",
    }
    trip_res = await client.post(
        "/api/v1/trips",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert trip_res.status_code == 201

    # 2. Get list of trips
    list_res = await client.get(
        "/api/v1/trips",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1

    # 3. Get savings summary
    savings_res = await client.get(
        "/api/v1/trips/savings?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert savings_res.status_code == 200
    savings = savings_res.json()
    assert savings["trip_count"] == 1
    assert float(savings["total_spend"]) > 0
    assert "savings_disclaimer" in savings
