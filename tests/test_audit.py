from httpx import AsyncClient
from sqlalchemy import select

from app.models.audit import AuditLog
from tests.conftest import TestSessionLocal, create_user, register_gym


async def test_register_login_and_user_create_write_audit_log(client: AsyncClient):
    admin = await register_gym(client, "auditalpha")
    admin_token = admin["tokens"]["access_token"]

    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@auditalpha.com", "password": "supersecret123"},
    )
    await create_user(client, admin_token, "auditalpha", "trainer", "trainer")

    async with TestSessionLocal() as session:
        result = await session.scalars(
            select(AuditLog).order_by(AuditLog.created_at.asc())
        )
        logs = result.all()

    actions = [log.action for log in logs]
    assert "auth.register" in actions
    assert "auth.login" in actions
    assert "user.created" in actions
    for log in logs:
        assert log.ip_address is not None
