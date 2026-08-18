import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.audit import client_ip, log_action
from app.services.auth import authenticate_user, build_tokens, register_tenant_and_admin
from app.utils.rate_limit import limiter
from app.utils.security import create_access_token, decode_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar gimnasio y admin",
    description="Crea un nuevo gimnasio (tenant) junto con su usuario administrador inicial "
    "y devuelve los tokens de acceso.",
)
@limiter.limit("10/minute")
async def register(
    request: Request, data: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await register_tenant_and_admin(db, data)
    access_token, refresh_token = build_tokens(user)
    await log_action(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="auth.register",
        resource="tenant",
        resource_id=user.tenant_id,
        ip_address=client_ip(request),
    )
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(access_token=access_token, refresh_token=refresh_token),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Autentica a un usuario con email y contraseña, y devuelve access y refresh token.",
)
@limiter.limit("10/minute")
async def login(
    request: Request, data: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await authenticate_user(db, data)
    access_token, refresh_token = build_tokens(user)
    await log_action(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="auth.login",
        resource="user",
        resource_id=user.id,
        ip_address=client_ip(request),
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar access token",
    description="Genera un nuevo access token a partir de un refresh token válido.",
)
@limiter.limit("20/minute")
async def refresh(
    request: Request, data: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    payload = decode_token(data.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Refresh token inválido", "code": "INVALID_REFRESH_TOKEN"},
        )
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Refresh token inválido", "code": "INVALID_REFRESH_TOKEN"},
        ) from exc
    user = await db.get(User, user_uuid)
    if user is None or user.is_deleted or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Refresh token inválido", "code": "INVALID_REFRESH_TOKEN"},
        )
    access_token = create_access_token(user_id, tenant_id)
    return TokenResponse(access_token=access_token, refresh_token=data.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Perfil propio",
    description="Devuelve los datos del usuario autenticado actualmente.",
)
async def me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user
