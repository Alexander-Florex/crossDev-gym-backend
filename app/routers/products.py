import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services import products as products_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/products", tags=["products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto",
    description="Da de alta un producto para la venta (agua, suplementos, etc.).",
)
async def create_product(
    request: Request,
    data: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    product = await products_service.create_product(db, current_user.tenant_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="product.created",
        resource="product",
        resource_id=product.id,
        details={"name": product.name},
        ip_address=client_ip(request),
    )
    return product


@router.get(
    "",
    response_model=Page[ProductResponse],
    summary="Listar productos",
    description="Lista paginada de productos disponibles para la venta.",
)
async def list_products(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    only_active: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    products, total = await products_service.list_products(
        db, current_user.tenant_id, page, size, only_active
    )
    return build_page([ProductResponse.model_validate(p) for p in products], total, page, size)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Obtener producto",
    description="Devuelve el detalle de un producto por id.",
)
async def get_product(
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return await products_service.get_product(db, current_user.tenant_id, product_id)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Actualizar producto",
    description="Actualiza precio, stock u otros datos de un producto.",
)
async def update_product(
    request: Request,
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    product = await products_service.update_product(db, current_user.tenant_id, product_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="product.updated",
        resource="product",
        resource_id=product.id,
        details=data.model_dump(exclude_unset=True, mode="json"),
        ip_address=client_ip(request),
    )
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar producto",
    description="Elimina un producto del catálogo de venta.",
)
async def delete_product(
    request: Request,
    product_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    await products_service.delete_product(db, current_user.tenant_id, product_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="product.deleted",
        resource="product",
        resource_id=product_id,
        ip_address=client_ip(request),
    )
