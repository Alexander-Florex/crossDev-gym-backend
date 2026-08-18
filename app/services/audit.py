import uuid

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def client_ip(request: Request | None) -> str | None:
    return request.client.host if request is not None and request.client else None


async def log_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    action: str,
    resource: str,
    resource_id: uuid.UUID | str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
    )
    await db.commit()
