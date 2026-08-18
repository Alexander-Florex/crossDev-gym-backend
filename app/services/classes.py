import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.class_ import Class
from app.models.user import User, UserRole
from app.repositories.base import TenantScopedRepository
from app.schemas.class_ import ClassCreate, ClassUpdate


async def _validate_trainer(db: AsyncSession, tenant_id: uuid.UUID, trainer_id: uuid.UUID) -> None:
    user_repo = TenantScopedRepository(db, User, tenant_id)
    trainer = await user_repo.get(trainer_id)
    if trainer is None or trainer.is_deleted or trainer.role != UserRole.trainer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": "trainer_id no corresponde a un personal trainer válido",
                "code": "INVALID_TRAINER",
            },
        )


async def create_class(db: AsyncSession, tenant_id: uuid.UUID, data: ClassCreate) -> Class:
    await _validate_trainer(db, tenant_id, data.trainer_id)

    repo = TenantScopedRepository(db, Class, tenant_id)
    gym_class = repo.add(
        Class(
            name=data.name,
            trainer_id=data.trainer_id,
            schedule=data.schedule,
            capacity=data.capacity,
        )
    )
    await db.commit()
    await db.refresh(gym_class)
    return gym_class


async def list_classes(
    db: AsyncSession, tenant_id: uuid.UUID, page: int, size: int, only_active: bool = False
) -> tuple[list[Class], int]:
    conditions = [Class.tenant_id == tenant_id]
    if only_active:
        conditions.append(Class.is_active.is_(True))

    total = await db.scalar(select(func.count()).select_from(Class).where(*conditions)) or 0
    stmt = (
        select(Class)
        .where(*conditions)
        .order_by(Class.schedule.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_class(db: AsyncSession, tenant_id: uuid.UUID, class_id: uuid.UUID) -> Class:
    repo = TenantScopedRepository(db, Class, tenant_id)
    gym_class = await repo.get(class_id)
    if gym_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Clase no encontrada", "code": "CLASS_NOT_FOUND"},
        )
    return gym_class


async def update_class(
    db: AsyncSession, tenant_id: uuid.UUID, class_id: uuid.UUID, data: ClassUpdate
) -> Class:
    gym_class = await get_class(db, tenant_id, class_id)
    payload = data.model_dump(exclude_unset=True)
    if "trainer_id" in payload:
        await _validate_trainer(db, tenant_id, payload["trainer_id"])
    for field, value in payload.items():
        setattr(gym_class, field, value)
    await db.commit()
    await db.refresh(gym_class)
    return gym_class


async def count_confirmed_bookings(db: AsyncSession, class_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Booking).where(
        Booking.class_id == class_id, Booking.status == BookingStatus.confirmed
    )
    return await db.scalar(stmt) or 0
