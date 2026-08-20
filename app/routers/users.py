import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import users as users_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea un personal trainer o alumno dentro del gimnasio del admin autenticado.",
)
async def create_user(
    request: Request,
    data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    user = await users_service.create_user(db, current_user.tenant_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="user.created",
        resource="user",
        resource_id=user.id,
        details={"role": user.role.value, "email": user.email},
        ip_address=client_ip(request),
    )
    return user


@router.get(
    "",
    response_model=Page[UserResponse],
    summary="Listar usuarios",
    description="Lista paginada de usuarios del gimnasio (personal trainers y alumnos).",
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
    role: UserRole | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = await users_service.list_users(db, current_user.tenant_id, page, size, role)
    return build_page([UserResponse.model_validate(u) for u in items], total, page, size)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Obtener usuario",
    description="Devuelve el detalle de un usuario del gimnasio por id.",
)
async def get_user(
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    return await users_service.get_user(db, current_user.tenant_id, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Actualizar usuario",
    description="Actualiza datos de un usuario del gimnasio (nombre, rol, estado, etc).",
)
async def update_user(
    request: Request,
    user_id: uuid.UUID,
    data: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    user = await users_service.update_user(db, current_user.tenant_id, user_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="user.updated",
        resource="user",
        resource_id=user.id,
        details=data.model_dump(exclude_unset=True),
        ip_address=client_ip(request),
    )
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario",
    description="Da de baja (soft delete) a un usuario del gimnasio.",
)
async def delete_user(
    request: Request,
    user_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    await users_service.soft_delete_user(db, current_user.tenant_id, user_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="user.deleted",
        resource="user",
        resource_id=user_id,
        ip_address=client_ip(request),
    )
