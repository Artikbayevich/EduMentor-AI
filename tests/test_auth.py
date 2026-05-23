import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    payload = {
        "email": "student@sezgi.edu",
        "username": "test_student",
        "password": "securepass123",
        "role": "student",
    }
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == payload["email"]

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()
