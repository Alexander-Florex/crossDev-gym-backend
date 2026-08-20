import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.base import TenantScopedRepository
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password


def _repo(db: AsyncSession, tenant_id: uuid.UUID) -> TenantScopedRepository[User]:
    return TenantScopedRepository(db, User, tenant_id)


async def create_user(db: AsyncSession, tenant_id: uuid.UUID, data: UserCreate) -> User:
    repo = _repo(db, tenant_id)
    existing = await repo.list(User.email == data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Ya existe un usuario con ese email", "code": "USER_EMAIL_TAKEN"},
        )

    user = repo.add(
        User(
            email=data.email,
            hashed_password=hash_password(data.password),
            role=data.role,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(
    db: AsyncSession, tenant_id: uuid.UUID, page: int, size: int, role: UserRole | None = None
) -> tuple[list[User], int]:
    base_conditions = (User.is_deleted.is_(False),)
    if role is not None:
        base_conditions = (*base_conditions, User.role == role)

    total_stmt = (
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id, *base_conditions)
    )
    total = await db.scalar(total_stmt) or 0

    stmt = (
        select(User)
        .where(User.tenant_id == tenant_id, *base_conditions)
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_user(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User:
    repo = _repo(db, tenant_id)
    user = await repo.get(user_id)
    if user is None or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Usuario no encontrado", "code": "USER_NOT_FOUND"},
        )
    return user


async def update_user(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, data: UserUpdate
) -> User:
    user = await get_user(db, tenant_id, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def soft_delete_user(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    user = await get_user(db, tenant_id, user_id)
    user.is_deleted = True
    user.deleted_at = datetime.now(UTC)
    user.is_active = False
    await db.commit()
