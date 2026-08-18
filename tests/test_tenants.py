from httpx import AsyncClient


async def test_admin_can_view_and_update_own_tenant(client: AsyncClient):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": "Gym Epsilon",
            "tenant_slug": "epsilon",
            "email": "admin@epsilon.com",
            "password": "supersecret123",
            "first_name": "Ana",
            "last_name": "Admin",
            "phone": None,
        },
    )
    token = register_response.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    get_response = await client.get("/api/v1/tenants/me", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["slug"] == "epsilon"
    assert get_response.json()["plan_type"] == "basic"

    patch_response = await client.patch(
        "/api/v1/tenants/me", json={"name": "Gym Epsilon Renamed"}, headers=headers
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Gym Epsilon Renamed"
