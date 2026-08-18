from httpx import AsyncClient


async def _register(client: AsyncClient, slug: str) -> dict:
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


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_admin_can_create_list_update_and_delete_user(client: AsyncClient):
    admin = await _register(client, "alpha")
    admin_token = admin["tokens"]["access_token"]

    create_response = await client.post(
        "/api/v1/users",
        json={
            "email": "trainer@alpha.com",
            "password": "trainerpass123",
            "first_name": "Tom",
            "last_name": "Trainer",
            "role": "trainer",
        },
        headers=_auth(admin_token),
    )
    assert create_response.status_code == 201
    trainer = create_response.json()
    assert trainer["role"] == "trainer"
    assert "hashed_password" not in trainer

    list_response = await client.get("/api/v1/users", headers=_auth(admin_token))
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 2
    assert body["page"] == 1

    update_response = await client.patch(
        f"/api/v1/users/{trainer['id']}",
        json={"first_name": "Tomas"},
        headers=_auth(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["first_name"] == "Tomas"

    delete_response = await client.delete(
        f"/api/v1/users/{trainer['id']}", headers=_auth(admin_token)
    )
    assert delete_response.status_code == 204

    get_after_delete = await client.get(
        f"/api/v1/users/{trainer['id']}", headers=_auth(admin_token)
    )
    assert get_after_delete.status_code == 404


async def test_users_are_isolated_by_tenant(client: AsyncClient):
    admin_a = await _register(client, "beta")
    admin_b = await _register(client, "gamma")

    create_response = await client.post(
        "/api/v1/users",
        json={
            "email": "trainer@beta.com",
            "password": "trainerpass123",
            "first_name": "Tom",
            "last_name": "Trainer",
            "role": "trainer",
        },
        headers=_auth(admin_a["tokens"]["access_token"]),
    )
    trainer_id = create_response.json()["id"]

    cross_tenant_get = await client.get(
        f"/api/v1/users/{trainer_id}", headers=_auth(admin_b["tokens"]["access_token"])
    )
    assert cross_tenant_get.status_code == 404

    list_response = await client.get(
        "/api/v1/users", headers=_auth(admin_b["tokens"]["access_token"])
    )
    assert list_response.json()["total"] == 1


async def test_non_admin_cannot_create_users(client: AsyncClient):
    admin = await _register(client, "delta")
    admin_token = admin["tokens"]["access_token"]

    create_student = await client.post(
        "/api/v1/users",
        json={
            "email": "student@delta.com",
            "password": "studentpass123",
            "first_name": "Sam",
            "last_name": "Student",
            "role": "student",
        },
        headers=_auth(admin_token),
    )
    assert create_student.status_code == 201

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@delta.com", "password": "studentpass123"},
    )
    student_token = login_response.json()["access_token"]

    forbidden_response = await client.post(
        "/api/v1/users",
        json={
            "email": "another@delta.com",
            "password": "somepassword123",
            "first_name": "X",
            "last_name": "Y",
            "role": "student",
        },
        headers=_auth(student_token),
    )
    assert forbidden_response.status_code == 403
