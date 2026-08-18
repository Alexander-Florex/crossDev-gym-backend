from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_tenant, require_role
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.tenant import TenantResponse, TenantUpdate
from app.services.audit import client_ip, log_action
from app.services.tenants import update_tenant

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


@router.get(
    "/me",
    response_model=TenantResponse,
    summary="Ver gimnasio propio",
    description="Devuelve los datos del gimnasio (tenant) del usuario autenticado.",
)
async def get_my_tenant(tenant: Annotated[Tenant, Depends(get_tenant)]):
    return tenant


@router.patch(
    "/me",
    response_model=TenantResponse,
    summary="Actualizar gimnasio propio",
    description="Actualiza nombre y configuración del gimnasio (tenant) actual.",
)
async def update_my_tenant(
    request: Request,
    data: TenantUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    tenant: Annotated[Tenant, Depends(get_tenant)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    updated = await update_tenant(db, tenant, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="tenant.updated",
        resource="tenant",
        resource_id=tenant.id,
        details=data.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    return updated
