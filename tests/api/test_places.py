"""
API tests for saved places and IDOR ownership authorization.
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
async def test_saved_places_crud_and_idor(client: AsyncClient):
    token1 = await get_user_token(client, "alice@example.com")
    token2 = await get_user_token(client, "bob@example.com")

    # 1. Alice creates a place
    place_payload = {
        "name": "My Home",
        "label": "home",
        "latitude": 12.9784,
        "longitude": 77.6385,
        "address": "Indiranagar",
    }
    create_res = await client.post(
        "/api/v1/places",
        json=place_payload,
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert create_res.status_code == 201
    place_id = create_res.json()["id"]

    # 2. Alice lists her places
    list_res = await client.get(
        "/api/v1/places",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Bob attempts to update Alice's place (IDOR check -> must return 404)
    bob_update = await client.patch(
        f"/api/v1/places/{place_id}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert bob_update.status_code == 404

    # 4. Bob attempts to delete Alice's place (IDOR check -> must return 404)
    bob_delete = await client.delete(
        f"/api/v1/places/{place_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert bob_delete.status_code == 404

    # 5. Alice successfully deletes her place
    alice_delete = await client.delete(
        f"/api/v1/places/{place_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert alice_delete.status_code == 204

