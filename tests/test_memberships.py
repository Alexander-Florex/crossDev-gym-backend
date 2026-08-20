from httpx import AsyncClient

from tests.conftest import auth_headers, create_user, register_gym


async def test_admin_can_create_and_manage_membership(client: AsyncClient):
    admin = await register_gym(client, "memalpha")
    admin_token = admin["tokens"]["access_token"]
    student = await create_user(client, admin_token, "memalpha", "student", "student")

    create_response = await client.post(
        "/api/v1/memberships",
        json={
            "user_id": student["id"],
            "plan_name": "Mensual",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "price": 15000,
        },
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    membership = create_response.json()
    assert membership["status"] == "active"

    update_response = await client.patch(
        f"/api/v1/memberships/{membership['id']}",
        json={"status": "suspended"},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "suspended"

    student_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@memalpha.com", "password": "studentpass123"},
    )
    student_token = student_login.json()["access_token"]

    own_list = await client.get("/api/v1/memberships", headers=auth_headers(student_token))
    assert own_list.status_code == 200
    assert own_list.json()["total"] == 1


async def test_membership_requires_student_role(client: AsyncClient):
    admin = await register_gym(client, "membeta")
    admin_token = admin["tokens"]["access_token"]
    trainer = await create_user(client, admin_token, "membeta", "trainer", "trainer")

    response = await client.post(
        "/api/v1/memberships",
        json={
            "user_id": trainer["id"],
            "plan_name": "Mensual",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "price": 15000,
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 422


async def test_list_memberships_filters_by_status(client: AsyncClient):
    admin = await register_gym(client, "memgamma")
    admin_token = admin["tokens"]["access_token"]
    student1 = await create_user(client, admin_token, "memgamma", "student", "student1")
    student2 = await create_user(client, admin_token, "memgamma", "student", "student2")

    membership1 = await client.post(
        "/api/v1/memberships",
        json={
            "user_id": student1["id"],
            "plan_name": "Mensual",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "price": 15000,
        },
        headers=auth_headers(admin_token),
    )
    await client.post(
        "/api/v1/memberships",
        json={
            "user_id": student2["id"],
            "plan_name": "Mensual",
            "start_date": "2026-01-01",
            "end_date": "2026-02-01",
            "price": 15000,
        },
        headers=auth_headers(admin_token),
    )
    await client.patch(
        f"/api/v1/memberships/{membership1.json()['id']}",
        json={"status": "suspended"},
        headers=auth_headers(admin_token),
    )

    suspended_only = await client.get(
        "/api/v1/memberships", params={"status": "suspended"}, headers=auth_headers(admin_token)
    )
    assert suspended_only.json()["total"] == 1
    assert suspended_only.json()["items"][0]["user_id"] == student1["id"]

    active_only = await client.get(
        "/api/v1/memberships", params={"status": "active"}, headers=auth_headers(admin_token)
    )
    assert active_only.json()["total"] == 1
    assert active_only.json()["items"][0]["user_id"] == student2["id"]
