import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_role
from app.models.routine import Routine
from app.models.user import User, UserRole
from app.repositories.base import TenantScopedRepository
from app.schemas.routine import RoutineCreate, RoutineResponse, RoutineUpdate
from app.services import routines as routines_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page
from app.utils.pdf import generate_routine_pdf

router = APIRouter(prefix="/api/v1/routines", tags=["routines"])


def _assert_can_view(current_user: User, routine: Routine) -> None:
    if current_user.role == UserRole.admin:
        return
    if current_user.role == UserRole.trainer and routine.trainer_id == current_user.id:
        return
    if current_user.role == UserRole.student and routine.student_id == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
    )


@router.post(
    "",
    response_model=RoutineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear rutina",
    description="Crea una rutina de entrenamiento para un alumno, con sus ejercicios.",
)
async def create_routine(
    request: Request,
    data: RoutineCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    if current_user.role == UserRole.trainer:
        trainer_id = current_user.id
    else:
        if data.trainer_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"detail": "trainer_id es requerido", "code": "TRAINER_ID_REQUIRED"},
            )
        trainer_id = data.trainer_id

    routine = await routines_service.create_routine(db, current_user.tenant_id, trainer_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="routine.created",
        resource="routine",
        resource_id=routine.id,
        details={"student_id": str(routine.student_id), "name": routine.name},
        ip_address=client_ip(request),
    )
    return routine


@router.get(
    "",
    response_model=Page[RoutineResponse],
    summary="Listar rutinas",
    description="Lista paginada de rutinas (alumno y trainer solo ven las propias).",
)
async def list_routines(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    student_id = current_user.id if current_user.role == UserRole.student else None
    trainer_id = current_user.id if current_user.role == UserRole.trainer else None
    items, total = await routines_service.list_routines(
        db, current_user.tenant_id, page, size, student_id, trainer_id
    )
    return build_page([RoutineResponse.model_validate(r) for r in items], total, page, size)


@router.get(
    "/{routine_id}",
    response_model=RoutineResponse,
    summary="Obtener rutina",
    description="Devuelve el detalle de una rutina con sus ejercicios.",
)
async def get_routine(
    routine_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    routine = await routines_service.get_routine(db, current_user.tenant_id, routine_id)
    _assert_can_view(current_user, routine)
    return routine


@router.patch(
    "/{routine_id}",
    response_model=RoutineResponse,
    summary="Actualizar rutina",
    description="Actualiza nombre, descripción o ejercicios de una rutina.",
)
async def update_routine(
    request: Request,
    routine_id: uuid.UUID,
    data: RoutineUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    routine = await routines_service.get_routine(db, current_user.tenant_id, routine_id)
    _assert_can_view(current_user, routine)
    updated = await routines_service.update_routine(db, current_user.tenant_id, routine_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="routine.updated",
        resource="routine",
        resource_id=routine_id,
        ip_address=client_ip(request),
    )
    return updated


@router.delete(
    "/{routine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar rutina",
    description="Elimina una rutina y sus ejercicios.",
)
async def delete_routine(
    request: Request,
    routine_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    routine = await routines_service.get_routine(db, current_user.tenant_id, routine_id)
    _assert_can_view(current_user, routine)
    await routines_service.delete_routine(db, current_user.tenant_id, routine_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="routine.deleted",
        resource="routine",
        resource_id=routine_id,
        ip_address=client_ip(request),
    )


@router.get(
    "/{routine_id}/pdf",
    summary="Descargar PDF de rutina",
    description="Genera y descarga la rutina en formato PDF, lista para imprimir o compartir.",
)
async def download_routine_pdf(
    routine_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    routine = await routines_service.get_routine(db, current_user.tenant_id, routine_id)
    _assert_can_view(current_user, routine)

    user_repo = TenantScopedRepository(db, User, current_user.tenant_id)
    student = await user_repo.get(routine.student_id)
    trainer = await user_repo.get(routine.trainer_id)

    pdf_bytes = generate_routine_pdf(
        routine,
        student_name=f"{student.first_name} {student.last_name}" if student else "N/A",
        trainer_name=f"{trainer.first_name} {trainer.last_name}" if trainer else "N/A",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="rutina-{routine.id}.pdf"'},
    )
