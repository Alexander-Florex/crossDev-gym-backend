import os
from collections.abc import AsyncGenerator

os.environ["DISABLE_RATE_LIMIT"] = "1"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import *  # noqa: F401,F403,E402

settings = get_settings()

test_engine = create_async_engine(settings.test_database_url, future=True, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _reset_database() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_gym(client: AsyncClient, slug: str) -> dict:
    payload = {
        "tenant_name": f"Gym {slug}",
        "tenant_slug": slug,
        "email": f"admin@{slug}.com",
        "password": "supersecret123",
        "first_name": "Admin",
        "last_name": slug,
        "phone": None,
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def create_user(
    client: AsyncClient, admin_token: str, slug: str, role: str, prefix: str
) -> dict:
    response = await client.post(
        "/api/v1/users",
        json={
            "email": f"{prefix}@{slug}.com",
            "password": f"{prefix}pass123",
            "first_name": prefix.capitalize(),
            "last_name": "Test",
            "role": role,
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()
