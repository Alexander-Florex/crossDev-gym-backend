import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.booking import BookingStatus
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, BookingResponse
from app.services import bookings as bookings_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reservar clase",
    description="Reserva un cupo en una clase. El alumno reserva para sí mismo; "
    "el admin puede reservar en nombre de un alumno (reserva manual).",
)
async def create_booking(
    request: Request,
    data: BookingCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if current_user.role == UserRole.student:
        student_id = current_user.id
    elif current_user.role == UserRole.admin:
        if data.student_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"detail": "student_id es requerido", "code": "STUDENT_ID_REQUIRED"},
            )
        student_id = data.student_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
        )

    booking = await bookings_service.create_booking(
        db, current_user.tenant_id, data.class_id, student_id
    )
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="booking.created",
        resource="booking",
        resource_id=booking.id,
        details={"class_id": str(booking.class_id), "student_id": str(booking.student_id)},
        ip_address=client_ip(request),
    )
    return booking


@router.get(
    "",
    response_model=Page[BookingResponse],
    summary="Listar reservas",
    description="Lista paginada de reservas (el alumno solo ve las propias).",
)
async def list_bookings(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    class_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    status: BookingStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    if current_user.role == UserRole.student:
        student_id = current_user.id
    items, total = await bookings_service.list_bookings(
        db, current_user.tenant_id, page, size, student_id, class_id, status
    )
    return build_page([BookingResponse.model_validate(b) for b in items], total, page, size)


@router.delete(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Cancelar reserva",
    description="Cancela una reserva existente (libera el cupo de la clase).",
)
async def cancel_booking(
    request: Request,
    booking_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    booking = await bookings_service.get_booking(db, current_user.tenant_id, booking_id)
    if current_user.role == UserRole.student and booking.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
        )
    if current_user.role not in (UserRole.admin, UserRole.student):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
        )
    cancelled = await bookings_service.cancel_booking(db, current_user.tenant_id, booking_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="booking.cancelled",
        resource="booking",
        resource_id=cancelled.id,
        ip_address=client_ip(request),
    )
    return cancelled
