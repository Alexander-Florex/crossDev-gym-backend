from httpx import AsyncClient

from tests.conftest import auth_headers, create_user, register_gym


async def test_trainer_creates_routine_with_exercises_and_downloads_pdf(client: AsyncClient):
    admin = await register_gym(client, "rtnalpha")
    admin_token = admin["tokens"]["access_token"]
    trainer = await create_user(client, admin_token, "rtnalpha", "trainer", "trainer")
    student = await create_user(client, admin_token, "rtnalpha", "student", "student")

    trainer_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "trainer@rtnalpha.com", "password": "trainerpass123"},
    )
    trainer_token = trainer_login.json()["access_token"]

    create_response = await client.post(
        "/api/v1/routines",
        json={
            "student_id": student["id"],
            "name": "Fuerza semana 1",
            "description": "Enfoque en tren superior",
            "exercises": [
                {"exercise_name": "Press banca", "sets": 4, "reps": 8, "weight": 60},
                {"exercise_name": "Remo con barra", "sets": 4, "reps": 10},
            ],
        },
        headers=auth_headers(trainer_token),
    )
    assert create_response.status_code == 201, create_response.text
    routine = create_response.json()
    assert routine["trainer_id"] == trainer["id"]
    assert len(routine["exercises"]) == 2

    pdf_response = await client.get(
        f"/api/v1/routines/{routine['id']}/pdf", headers=auth_headers(trainer_token)
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content[:4] == b"%PDF"

    student_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@rtnalpha.com", "password": "studentpass123"},
    )
    student_token = student_login.json()["access_token"]

    student_view = await client.get(
        f"/api/v1/routines/{routine['id']}", headers=auth_headers(student_token)
    )
    assert student_view.status_code == 200


async def test_other_trainer_cannot_view_routine(client: AsyncClient):
    admin = await register_gym(client, "rtnbeta")
    admin_token = admin["tokens"]["access_token"]
    await create_user(client, admin_token, "rtnbeta", "trainer", "trainer")
    other_trainer = await create_user(client, admin_token, "rtnbeta", "trainer", "othertrainer")
    student = await create_user(client, admin_token, "rtnbeta", "student", "student")

    trainer_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "trainer@rtnbeta.com", "password": "trainerpass123"},
    )
    trainer_token = trainer_login.json()["access_token"]

    create_response = await client.post(
        "/api/v1/routines",
        json={"student_id": student["id"], "name": "Rutina X", "exercises": []},
        headers=auth_headers(trainer_token),
    )
    routine_id = create_response.json()["id"]

    other_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "othertrainer@rtnbeta.com", "password": "othertrainerpass123"},
    )
    other_token = other_login.json()["access_token"]

    forbidden_response = await client.get(
        f"/api/v1/routines/{routine_id}", headers=auth_headers(other_token)
    )
    assert forbidden_response.status_code == 403
    assert other_trainer["role"] == "trainer"
