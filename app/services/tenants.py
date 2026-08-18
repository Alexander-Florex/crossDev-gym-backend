from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.schemas.tenant import TenantUpdate


async def update_tenant(db: AsyncSession, tenant: Tenant, data: TenantUpdate) -> Tenant:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant
