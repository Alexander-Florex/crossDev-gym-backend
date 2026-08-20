import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, MembershipStatus
from app.models.user import User, UserRole
from app.repositories.base import TenantScopedRepository
from app.schemas.membership import MembershipCreate, MembershipUpdate


async def _get_target_student(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
    user_repo = TenantScopedRepository(db, User, tenant_id)
    user = await user_repo.get(user_id)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Usuario no encontrado", "code": "USER_NOT_FOUND"},
        )
    if user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "detail": "Solo se pueden crear membresías para alumnos",
                "code": "MEMBERSHIP_TARGET_NOT_STUDENT",
            },
        )
    return user


async def create_membership(
    db: AsyncSession, tenant_id: uuid.UUID, data: MembershipCreate
) -> Membership:
    await _get_target_student(db, tenant_id, data.user_id)

    repo = TenantScopedRepository(db, Membership, tenant_id)
    membership = repo.add(
        Membership(
            user_id=data.user_id,
            plan_name=data.plan_name,
            period=data.period,
            start_date=data.start_date,
            end_date=data.end_date,
            price=data.price,
        )
    )
    await db.commit()
    await db.refresh(membership)
    return membership


async def list_memberships(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int,
    size: int,
    user_id: uuid.UUID | None = None,
    status_filter: MembershipStatus | None = None,
) -> tuple[list[Membership], int]:
    conditions = [Membership.tenant_id == tenant_id]
    if user_id is not None:
        conditions.append(Membership.user_id == user_id)
    if status_filter is not None:
        conditions.append(Membership.status == status_filter)

    total = await db.scalar(select(func.count()).select_from(Membership).where(*conditions)) or 0
    stmt = (
        select(Membership)
        .where(*conditions)
        .order_by(Membership.start_date.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_membership(
    db: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
) -> Membership:
    repo = TenantScopedRepository(db, Membership, tenant_id)
    membership = await repo.get(membership_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Membresía no encontrada", "code": "MEMBERSHIP_NOT_FOUND"},
        )
    return membership


async def update_membership(
    db: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID, data: MembershipUpdate
) -> Membership:
    membership = await get_membership(db, tenant_id, membership_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(membership, field, value)
    await db.commit()
    await db.refresh(membership)
    return membership


async def delete_membership(
    db: AsyncSession, tenant_id: uuid.UUID, membership_id: uuid.UUID
) -> None:
    membership = await get_membership(db, tenant_id, membership_id)
    await db.delete(membership)
    await db.commit()
