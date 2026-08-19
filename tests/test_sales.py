from httpx import AsyncClient

from tests.conftest import auth_headers, create_user, register_gym


async def test_product_sale_discounts_stock(client: AsyncClient):
    admin = await register_gym(client, "salealpha")
    admin_token = admin["tokens"]["access_token"]

    product_response = await client.post(
        "/api/v1/products",
        json={"name": "Monster", "price": 2500, "stock_quantity": 10},
        headers=auth_headers(admin_token),
    )
    product = product_response.json()

    sale_response = await client.post(
        "/api/v1/sales/products",
        json={
            "items": [{"product_id": product["id"], "quantity": 3}],
            "payment_method": "cash",
        },
        headers=auth_headers(admin_token),
    )
    assert sale_response.status_code == 201
    sale = sale_response.json()
    assert sale["sale_type"] == "product"
    assert float(sale["amount"]) == 7500

    product_after = await client.get(
        f"/api/v1/products/{product['id']}", headers=auth_headers(admin_token)
    )
    assert product_after.json()["stock_quantity"] == 7


async def test_product_sale_fails_with_insufficient_stock(client: AsyncClient):
    admin = await register_gym(client, "salebeta")
    admin_token = admin["tokens"]["access_token"]

    product_response = await client.post(
        "/api/v1/products",
        json={"name": "Creatina", "price": 15000, "stock_quantity": 1},
        headers=auth_headers(admin_token),
    )
    product = product_response.json()

    sale_response = await client.post(
        "/api/v1/sales/products",
        json={
            "items": [{"product_id": product["id"], "quantity": 5}],
            "payment_method": "card",
        },
        headers=auth_headers(admin_token),
    )
    assert sale_response.status_code == 422


async def test_membership_payment_registers_sale(client: AsyncClient):
    admin = await register_gym(client, "salegamma")
    admin_token = admin["tokens"]["access_token"]
    student = await create_user(client, admin_token, "salegamma", "student", "student")

    membership_response = await client.post(
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
    membership = membership_response.json()

    pay_response = await client.post(
        f"/api/v1/sales/memberships/{membership['id']}/pay",
        json={"payment_method": "transfer"},
        headers=auth_headers(admin_token),
    )
    assert pay_response.status_code == 201
    sale = pay_response.json()
    assert sale["sale_type"] == "membership"
    assert float(sale["amount"]) == 15000
    assert sale["membership_id"] == membership["id"]

    list_response = await client.get(
        "/api/v1/sales", params={"sale_type": "membership"}, headers=auth_headers(admin_token)
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


async def test_cancel_product_sale_restocks(client: AsyncClient):
    admin = await register_gym(client, "saledelta")
    admin_token = admin["tokens"]["access_token"]

    product_response = await client.post(
        "/api/v1/products",
        json={"name": "Proteina", "price": 20000, "stock_quantity": 5},
        headers=auth_headers(admin_token),
    )
    product = product_response.json()

    sale_response = await client.post(
        "/api/v1/sales/products",
        json={
            "items": [{"product_id": product["id"], "quantity": 2}],
            "payment_method": "cash",
        },
        headers=auth_headers(admin_token),
    )
    sale = sale_response.json()

    cancel_response = await client.post(
        f"/api/v1/sales/{sale['id']}/cancel", headers=auth_headers(admin_token)
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    product_after = await client.get(
        f"/api/v1/products/{product['id']}", headers=auth_headers(admin_token)
    )
    assert product_after.json()["stock_quantity"] == 5
