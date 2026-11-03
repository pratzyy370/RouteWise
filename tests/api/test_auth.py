"""
API tests for authentication, JWT issuance, and profile endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "testuser@example.com",
        "password": "Password123!",
        "full_name": "Test User",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "testuser@example.com"
    assert "id" in user_data

    # 2. Reject duplicate registration
    dup_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_res.status_code == 409

    # 3. Login
    login_payload = {
        "email": "testuser@example.com",
        "password": "Password123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    token = token_data["access_token"]

    # 4. Access protected profile
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testuser@example.com"

    # 5. Access without token should fail 401
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

