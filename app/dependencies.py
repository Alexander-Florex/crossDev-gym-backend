import uuid
from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.utils.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"detail": "No se pudo validar la credencial", "code": "INVALID_TOKEN"},
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise CREDENTIALS_EXCEPTION

    user_id = payload.get("sub")
    if user_id is None:
        raise CREDENTIALS_EXCEPTION

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError as exc:
        raise CREDENTIALS_EXCEPTION from exc

    user = await db.get(User, user_uuid)
    if user is None or user.is_deleted:
        raise CREDENTIALS_EXCEPTION
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"detail": "Usuario inactivo", "code": "USER_INACTIVE"},
        )
    return current_user


def require_role(
    *roles: UserRole,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    async def dependency(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"detail": "No tenés permisos para esta acción", "code": "FORBIDDEN_ROLE"},
            )
        return current_user

    return dependency


async def get_tenant(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Tenant:
    tenant = await db.get(Tenant, current_user.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Tenant no encontrado", "code": "TENANT_NOT_FOUND"},
        )
    return tenant
