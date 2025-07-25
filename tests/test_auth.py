from unittest.mock import patch

import pytest
from httpx import AsyncClient
from services.database import get_db


@pytest.mark.anyio
async def test_register_user(client: AsyncClient):
    get_db().users.delete_one({"username": "testuser"})
    response = await client.post("/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_login_user(client: AsyncClient):
    response = await client.post("/token", json={
        "username": "testuser",
        "password": "testpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.anyio
async def test_password_recovery(client: AsyncClient):
    email = "testuser@example.com"
    response = await client.post("/password-recovery", json={"email": email})
    assert response.status_code == 200
    assert response.json()["message"] == "Password recovery email sent"


@pytest.mark.anyio
async def test_password_reset(client: AsyncClient, token: str):
    new_password = "new_password123"
    response = await client.post("/password-reset", json={"token": token, "new_password": new_password})
    assert response.status_code == 200
    assert response.json()["message"] == "Password has been reset"


@pytest.mark.anyio
@patch("server.routes.auth.id_token.verify_oauth2_token")
async def test_google_login(mock_verify_oauth2_token, client: AsyncClient):
    get_db().users.delete_one({"username": "testuser1"})
    mock_verify_oauth2_token.return_value = {"email": "testuser@test.com"}
    response = await client.post("/google-login", json={"accessToken": "mock_code"})
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["username"] == "testuser1"
