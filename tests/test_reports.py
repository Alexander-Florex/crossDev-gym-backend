from httpx import AsyncClient

from tests.conftest import auth_headers, create_user, register_gym


async def test_overview_report_reflects_tenant_state(client: AsyncClient):
    admin = await register_gym(client, "repalpha")
    admin_token = admin["tokens"]["access_token"]
    await create_user(client, admin_token, "repalpha", "trainer", "trainer")
    await create_user(client, admin_token, "repalpha", "student", "student")

    response = await client.get("/api/v1/reports/overview", headers=auth_headers(admin_token))
    assert response.status_code == 200
    body = response.json()
    assert body["active_students"] == 1
    assert body["active_trainers"] == 1
    assert body["memberships_active"] == 0


async def test_overview_report_requires_admin(client: AsyncClient):
    admin = await register_gym(client, "repbeta")
    admin_token = admin["tokens"]["access_token"]
    await create_user(client, admin_token, "repbeta", "trainer", "trainer")

    trainer_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "trainer@repbeta.com", "password": "trainerpass123"},
    )
    trainer_token = trainer_login.json()["access_token"]

    response = await client.get("/api/v1/reports/overview", headers=auth_headers(trainer_token))
    assert response.status_code == 403
