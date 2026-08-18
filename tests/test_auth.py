from httpx import AsyncClient

REGISTER_PAYLOAD = {
    "tenant_name": "Gimnasio Titanes",
    "tenant_slug": "titanes",
    "email": "admin@titanes.com",
    "password": "supersecret123",
    "first_name": "Ana",
    "last_name": "Gomez",
    "phone": "+541122334455",
}


async def test_register_then_login_flow(client: AsyncClient):
    register_response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert register_response.status_code == 201
    register_body = register_response.json()
    assert register_body["user"]["email"] == REGISTER_PAYLOAD["email"]
    assert "hashed_password" not in register_body["user"]
    assert register_body["tokens"]["access_token"]

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["email"] == REGISTER_PAYLOAD["email"]
    assert me_body["role"] == "admin"


async def test_login_with_wrong_password_fails(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401
