"""Pytest fixtures: SQLite test DB, ASGI client, fake Redis, auth helpers."""
import os

# Configure a throwaway SQLite DB + test secret BEFORE importing the app.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:////tmp/csp_test.db"
os.environ["JWT_SECRET"] = "test-secret"
# Empty AI key → heuristic fallback, so tests never hit the network.
# (Set here to override any real key in backend/.env.)
os.environ["AI_API_KEY"] = ""

import httpx
import pytest
import pytest_asyncio

import app.core.redis_client as redis_client
from app.db.base import Base
from app.db.session import engine
from app.main import app


class FakeRedis:
    """Minimal in-memory async Redis stand-in for cache tests."""

    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)

    async def ping(self):
        return True

    async def aclose(self):
        pass


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    redis_client._client = None  # default: no cache
    yield


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def fake_redis():
    """Activate an in-memory Redis for the duration of a test."""
    fake = FakeRedis()
    redis_client._client = fake
    yield fake
    redis_client._client = None


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client, email, password="password123", role="csm", name=None):
    r = await client.post(
        "/api/v1/auth/register",
        json={"name": name or email, "email": email, "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    return body["access_token"], body["user"]["id"]
