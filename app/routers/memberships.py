import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.schemas.membership import MembershipCreate, MembershipResponse, MembershipUpdate
from app.services import memberships as memberships_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/memberships", tags=["memberships"])


@router.post(
    "",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear membresía",
    description="Da de alta una membresía para un alumno del gimnasio.",
)
async def create_membership(
    request: Request,
    data: MembershipCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    membership = await memberships_service.create_membership(db, current_user.tenant_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="membership.created",
        resource="membership",
        resource_id=membership.id,
        details={"user_id": str(membership.user_id), "plan_name": membership.plan_name},
        ip_address=client_ip(request),
    )
    return membership


@router.get(
    "",
    response_model=Page[MembershipResponse],
    summary="Listar membresías",
    description="Lista paginada de membresías del gimnasio (el alumno solo ve las propias).",
)
async def list_memberships(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    user_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    if current_user.role == UserRole.student:
        user_id = current_user.id
    elif current_user.role not in (UserRole.admin, UserRole.trainer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
        )

    items, total = await memberships_service.list_memberships(
        db, current_user.tenant_id, page, size, user_id
    )
    return build_page([MembershipResponse.model_validate(m) for m in items], total, page, size)


@router.get(
    "/{membership_id}",
    response_model=MembershipResponse,
    summary="Obtener membresía",
    description="Devuelve el detalle de una membresía por id.",
)
async def get_membership(
    membership_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    membership = await memberships_service.get_membership(
        db, current_user.tenant_id, membership_id
    )
    if current_user.role == UserRole.student and membership.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
        )
    return membership


@router.patch(
    "/{membership_id}",
    response_model=MembershipResponse,
    summary="Actualizar membresía",
    description="Actualiza plan, fechas, precio o estado (activa/vencida/suspendida).",
)
async def update_membership(
    request: Request,
    membership_id: uuid.UUID,
    data: MembershipUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    membership = await memberships_service.update_membership(
        db, current_user.tenant_id, membership_id, data
    )
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="membership.updated",
        resource="membership",
        resource_id=membership.id,
        details=data.model_dump(exclude_unset=True, mode="json"),
        ip_address=client_ip(request),
    )
    return membership


@router.delete(
    "/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar membresía",
    description="Elimina una membresía del gimnasio.",
)
async def delete_membership(
    request: Request,
    membership_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    await memberships_service.delete_membership(db, current_user.tenant_id, membership_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="membership.deleted",
        resource="membership",
        resource_id=membership_id,
        ip_address=client_ip(request),
    )
