from httpx import AsyncClient

from tests.conftest import auth_headers, register_gym


async def test_admin_can_manage_product(client: AsyncClient):
    admin = await register_gym(client, "prodalpha")
    admin_token = admin["tokens"]["access_token"]

    create_response = await client.post(
        "/api/v1/products",
        json={"name": "Agua 500ml", "price": 800, "stock_quantity": 50},
        headers=auth_headers(admin_token),
    )
    assert create_response.status_code == 201
    product = create_response.json()
    assert product["stock_quantity"] == 50

    update_response = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"price": 900},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200
    assert float(update_response.json()["price"]) == 900

    list_response = await client.get("/api/v1/products", headers=auth_headers(admin_token))
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
