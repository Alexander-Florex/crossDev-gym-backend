from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)


async def register_tenant_and_admin(db: AsyncSession, data: RegisterRequest) -> User:
    existing_tenant = await db.scalar(select(Tenant).where(Tenant.slug == data.tenant_slug))
    if existing_tenant is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"detail": "Ya existe un gimnasio con ese slug", "code": "TENANT_SLUG_TAKEN"},
        )

    tenant = Tenant(name=data.tenant_name, slug=data.tenant_slug)
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole.admin,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> User:
    result = await db.execute(
        select(User).where(User.email == data.email, User.is_deleted.is_(False))
    )
    user = result.scalars().first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Credenciales inválidas", "code": "INVALID_CREDENTIALS"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Usuario inactivo", "code": "USER_INACTIVE"},
        )
    return user


def build_tokens(user: User) -> tuple[str, str]:
    access = create_access_token(str(user.id), str(user.tenant_id))
    refresh = create_refresh_token(str(user.id), str(user.tenant_id))
    return access, refresh
