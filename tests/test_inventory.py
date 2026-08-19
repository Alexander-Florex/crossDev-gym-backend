from httpx import AsyncClient

from tests.conftest import auth_headers, register_gym


async def test_admin_can_manage_inventory_item(client: AsyncClient):
    admin = await register_gym(client, "invalpha")
    admin_token = admin["tokens"]["access_token"]

    create_response = await client.post(
        "/api/v1/inventory",
        json={"name": "Mancuernas 10kg", "category": "equipment", "quantity": 20},
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    item = create_response.json()
    assert item["quantity"] == 20

    update_response = await client.patch(
        f"/api/v1/inventory/{item['id']}",
        json={"quantity": 18},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["quantity"] == 18

    list_response = await client.get("/api/v1/inventory", headers=auth_headers(admin_token))
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    delete_response = await client.delete(
        f"/api/v1/inventory/{item['id']}", headers=auth_headers(admin_token)
    )
    assert delete_response.status_code == 204
