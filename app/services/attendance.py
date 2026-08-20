import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.class_ import Class
from app.models.user import User
from app.repositories.base import TenantScopedRepository


async def check_in(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, class_id: uuid.UUID | None
) -> Attendance:
    user_repo = TenantScopedRepository(db, User, tenant_id)
    user = await user_repo.get(user_id)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Usuario no encontrado", "code": "USER_NOT_FOUND"},
        )

    if class_id is not None:
        class_repo = TenantScopedRepository(db, Class, tenant_id)
        gym_class = await class_repo.get(class_id)
        if gym_class is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"detail": "Clase no encontrada", "code": "CLASS_NOT_FOUND"},
            )

    repo = TenantScopedRepository(db, Attendance, tenant_id)
    attendance = repo.add(Attendance(user_id=user_id, class_id=class_id))
    await db.commit()
    await db.refresh(attendance)
    return attendance


async def list_attendance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int,
    size: int,
    user_id: uuid.UUID | None = None,
    class_id: uuid.UUID | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
) -> tuple[list[Attendance], int]:
    conditions = [Attendance.tenant_id == tenant_id]
    if user_id is not None:
        conditions.append(Attendance.user_id == user_id)
    if class_id is not None:
        conditions.append(Attendance.class_id == class_id)
    if from_ is not None:
        conditions.append(Attendance.checked_in_at >= from_)
    if to is not None:
        conditions.append(Attendance.checked_in_at <= to)

    total = await db.scalar(select(func.count()).select_from(Attendance).where(*conditions)) or 0
    stmt = (
        select(Attendance)
        .where(*conditions)
        .order_by(Attendance.checked_in_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total
