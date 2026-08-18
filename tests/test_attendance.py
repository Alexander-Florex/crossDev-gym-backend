from httpx import AsyncClient

from tests.conftest import auth_headers, create_user, register_gym


async def test_student_self_check_in_and_admin_check_in(client: AsyncClient):
    admin = await register_gym(client, "attalpha")
    admin_token = admin["tokens"]["access_token"]
    student = await create_user(client, admin_token, "attalpha", "student", "student")

    student_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@attalpha.com", "password": "studentpass123"},
    )
    student_token = student_login.json()["access_token"]

    self_checkin = await client.post(
        "/api/v1/attendance", json={}, headers=auth_headers(student_token)
    )
    assert self_checkin.status_code == 201
    assert self_checkin.json()["user_id"] == student["id"]

    admin_checkin = await client.post(
        "/api/v1/attendance", json={"user_id": student["id"]}, headers=auth_headers(admin_token)
    )
    assert admin_checkin.status_code == 201

    list_response = await client.get("/api/v1/attendance", headers=auth_headers(admin_token))
    assert list_response.json()["total"] == 2

    student_list = await client.get("/api/v1/attendance", headers=auth_headers(student_token))
    assert student_list.json()["total"] == 2


async def test_admin_checkin_requires_user_id(client: AsyncClient):
    admin = await register_gym(client, "attbeta")
    admin_token = admin["tokens"]["access_token"]

    response = await client.post("/api/v1/attendance", json={}, headers=auth_headers(admin_token))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "USER_ID_REQUIRED"
