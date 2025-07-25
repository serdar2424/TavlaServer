import os
import sys
from datetime import timedelta

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from services.database import initialize_db_connection, create_indexes, get_db, default_id
from httpx import AsyncClient
from services.auth import create_access_token
from core.config import ACCESS_TOKEN_EXPIRE_MINUTES


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    # Initialize the database connection
    initialize_db_connection()
    await create_indexes()

    # Remove the test user if it exists
    await clear_db()

    async with AsyncClient(app=app, base_url="http://test") as client:
        print("Client is ready")
        yield client


async def clear_db():
    db = get_db()
    await db.users.delete_one({"username": "testuser"})
    await db.users.delete_one({"username": "testuser2"})
    await db.matches.delete_many({"$or": [{"player1": "testuser"}, {"player2": "testuser"}]})
    await db.matches.delete_many({"$or": [{"player1": "testuser2"}, {"player2": "testuser2"}]})
    await db.matches.delete_many({"participants": "testuser"})
    await db.matches.delete_many({"participants": "testuser2"})
    await db.tournaments.delete_many({"owner": "testuser"})
    await db.users.insert_one({"username": "testuser", "email": "testuser@testuser.com", "_id": default_id(), "rating": 1500, "password":'testpw'})
    await db.users.insert_one({"username": "testuser2", "email": "testuser2@testuser.com", "_id": default_id(), "rating": 1500, "password":'testpw'})


async def clear_matches():
    db = get_db()
    await db.matches.delete_many({})

async def clear_tournaments():
    db = get_db()
    await db.tournaments.delete_many({})


@pytest.fixture(scope="session")
def token():
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    encoded_jwt = create_access_token(
        data={"sub": "testuser"}, expires_delta=access_token_expires
    )
    return encoded_jwt
