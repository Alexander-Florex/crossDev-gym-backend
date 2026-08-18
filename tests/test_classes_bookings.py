from httpx import AsyncClient

from tests.conftest import auth_headers, create_user, register_gym


async def _create_class(
    client: AsyncClient, admin_token: str, trainer_id: str, capacity: int = 2
) -> dict:
    response = await client.post(
        "/api/v1/classes",
        json={
            "name": "Funcional",
            "trainer_id": trainer_id,
            "schedule": "2026-03-01T10:00:00Z",
            "capacity": capacity,
        },
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_class_lifecycle_and_capacity(client: AsyncClient):
    admin = await register_gym(client, "clsalpha")
    admin_token = admin["tokens"]["access_token"]
    trainer = await create_user(client, admin_token, "clsalpha", "trainer", "trainer")
    gym_class = await _create_class(client, admin_token, trainer["id"], capacity=1)
    assert gym_class["available_spots"] == 1

    student1 = await create_user(client, admin_token, "clsalpha", "student", "student1")
    student2 = await create_user(client, admin_token, "clsalpha", "student", "student2")

    booking1 = await client.post(
        "/api/v1/bookings",
        json={"class_id": gym_class["id"], "student_id": student1["id"]},
        headers=auth_headers(admin_token),
    )
    assert booking1.status_code == 201
    assert booking1.json()["status"] == "confirmed"

    booking2 = await client.post(
        "/api/v1/bookings",
        json={"class_id": gym_class["id"], "student_id": student2["id"]},
        headers=auth_headers(admin_token),
    )
    assert booking2.status_code == 409
    assert booking2.json()["detail"]["code"] == "CLASS_FULL"

    get_class = await client.get(
        f"/api/v1/classes/{gym_class['id']}", headers=auth_headers(admin_token)
    )
    assert get_class.json()["available_spots"] == 0

    cancel_response = await client.delete(
        f"/api/v1/bookings/{booking1.json()['id']}", headers=auth_headers(admin_token)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    get_class_after = await client.get(
        f"/api/v1/classes/{gym_class['id']}", headers=auth_headers(admin_token)
    )
    assert get_class_after.json()["available_spots"] == 1


async def test_student_can_self_book_and_cannot_double_book(client: AsyncClient):
    admin = await register_gym(client, "clsbeta")
    admin_token = admin["tokens"]["access_token"]
    trainer = await create_user(client, admin_token, "clsbeta", "trainer", "trainer")
    gym_class = await _create_class(client, admin_token, trainer["id"], capacity=5)
    await create_user(client, admin_token, "clsbeta", "student", "student1")

    student_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student1@clsbeta.com", "password": "student1pass123"},
    )
    student_token = student_login.json()["access_token"]

    first_booking = await client.post(
        "/api/v1/bookings", json={"class_id": gym_class["id"]}, headers=auth_headers(student_token)
    )
    assert first_booking.status_code == 201

    duplicate_booking = await client.post(
        "/api/v1/bookings", json={"class_id": gym_class["id"]}, headers=auth_headers(student_token)
    )
    assert duplicate_booking.status_code == 409
    assert duplicate_booking.json()["detail"]["code"] == "DUPLICATE_BOOKING"
