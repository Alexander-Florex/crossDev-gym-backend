import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole
from app.repositories.base import TenantScopedRepository
from app.services.classes import count_confirmed_bookings, get_class


async def create_booking(
    db: AsyncSession, tenant_id: uuid.UUID, class_id: uuid.UUID, student_id: uuid.UUID
) -> Booking:
    gym_class = await get_class(db, tenant_id, class_id)
    if not gym_class.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": "La clase no está activa", "code": "CLASS_INACTIVE"},
        )

    user_repo = TenantScopedRepository(db, User, tenant_id)
    student = await user_repo.get(student_id)
    if student is None or student.is_deleted or student.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": "student_id no corresponde a un alumno válido",
                "code": "INVALID_STUDENT",
            },
        )

    existing_stmt = select(Booking).where(
        Booking.tenant_id == tenant_id,
        Booking.class_id == class_id,
        Booking.student_id == student_id,
        Booking.status == BookingStatus.confirmed,
    )
    existing = await db.scalar(existing_stmt)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "El alumno ya tiene una reserva en esta clase",
                "code": "DUPLICATE_BOOKING",
            },
        )

    confirmed_count = await count_confirmed_bookings(db, class_id)
    if confirmed_count >= gym_class.capacity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "La clase no tiene cupos disponibles", "code": "CLASS_FULL"},
        )

    repo = TenantScopedRepository(db, Booking, tenant_id)
    booking = repo.add(
        Booking(class_id=class_id, student_id=student_id, status=BookingStatus.confirmed)
    )
    await db.commit()
    await db.refresh(booking)
    return booking


async def list_bookings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int,
    size: int,
    student_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    status_filter: BookingStatus | None = None,
) -> tuple[list[Booking], int]:
    conditions = [Booking.tenant_id == tenant_id]
    if student_id is not None:
        conditions.append(Booking.student_id == student_id)
    if class_id is not None:
        conditions.append(Booking.class_id == class_id)
    if status_filter is not None:
        conditions.append(Booking.status == status_filter)

    total = await db.scalar(select(func.count()).select_from(Booking).where(*conditions)) or 0
    stmt = (
        select(Booking)
        .where(*conditions)
        .order_by(Booking.booked_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_booking(db: AsyncSession, tenant_id: uuid.UUID, booking_id: uuid.UUID) -> Booking:
    repo = TenantScopedRepository(db, Booking, tenant_id)
    booking = await repo.get(booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Reserva no encontrada", "code": "BOOKING_NOT_FOUND"},
        )
    return booking


async def cancel_booking(db: AsyncSession, tenant_id: uuid.UUID, booking_id: uuid.UUID) -> Booking:
    booking = await get_booking(db, tenant_id, booking_id)
    booking.status = BookingStatus.cancelled
    await db.commit()
    await db.refresh(booking)
    return booking
