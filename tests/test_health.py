from httpx import AsyncClient


async def test_health_check(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
