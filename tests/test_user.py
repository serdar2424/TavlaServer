import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_read_users_me(client: AsyncClient, token: str):
    response = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

@pytest.mark.anyio
async def test_get_users(client: AsyncClient, token: str):
    response = await client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.anyio
async def test_search_usernames(client: AsyncClient, token: str):
    response = await client.get("/users/search", params={"query": "test"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.anyio
async def test_get_top5_and_me(client: AsyncClient, token: str):
    response = await client.get("/users/top5_and_me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(data)
    assert data[-1]["username"] == "testuser"
    assert "position" in data[-1]

@pytest.mark.anyio
async def test_get_top5_and_me_google(client: AsyncClient, token: str):
    email_list = {
        "emails": [
            "asd@gmail.com",
            "testuser@example.com"
        ]
    }
    response = await client.post("/users/top5_and_me_google", json=email_list, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[-1]["username"] == "testuser"
    assert "position" in data[-1]

@pytest.mark.anyio
async def test_get_user_rating(client: AsyncClient, token: str):
    response = await client.get("/users/get_user_rating", params={"username": "testuser"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), int)
    response = await client.get("/users/get_user_rating", params={"username": "not_existing_user"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404