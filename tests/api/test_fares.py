"""
API tests for fare history, prediction, and alerts.
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
async def test_fare_history(client: AsyncClient):
    payload = {
        "origin": {"latitude": 12.9784, "longitude": 77.6385},
        "destination": {"latitude": 12.9756, "longitude": 77.6066},
        "days": 30,
    }
    response = await client.post("/api/v1/fares/history", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "average_fare" in data
    assert "is_demo_data" in data


@pytest.mark.asyncio
async def test_fare_alerts_workflow(client: AsyncClient):
    token = await get_user_token(client, "alertuser@example.com")

    # Create alert
    payload = {
        "origin_lat": 12.9784,
        "origin_lng": 77.6385,
        "dest_lat": 12.9756,
        "dest_lng": 77.6066,
        "origin_name": "Indiranagar",
        "dest_name": "MG Road",
        "target_fare": 65.0,
        "cooldown_minutes": 60,
    }
    res = await client.post(
        "/api/v1/fares/alerts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    alert_id = res.json()["id"]

    # List alerts
    list_res = await client.get(
        "/api/v1/fares/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Delete alert
    del_res = await client.delete(
        f"/api/v1/fares/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

