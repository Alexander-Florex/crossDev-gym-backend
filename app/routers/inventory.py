import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.inventory import InventoryItemCreate, InventoryItemResponse, InventoryItemUpdate
from app.services import inventory as inventory_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear ítem de inventario",
    description="Da de alta un ítem de inventario (equipamiento o consumible).",
)
async def create_item(
    request: Request,
    data: InventoryItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    item = await inventory_service.create_item(db, current_user.tenant_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="inventory_item.created",
        resource="inventory_item",
        resource_id=item.id,
        details={"name": item.name},
        ip_address=client_ip(request),
    )
    return item


@router.get(
    "",
    response_model=Page[InventoryItemResponse],
    summary="Listar inventario",
    description="Lista paginada de ítems de inventario del gimnasio.",
)
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = await inventory_service.list_items(db, current_user.tenant_id, page, size)
    return build_page([InventoryItemResponse.model_validate(i) for i in items], total, page, size)


@router.get(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Obtener ítem de inventario",
    description="Devuelve el detalle de un ítem de inventario por id.",
)
async def get_item(
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    return await inventory_service.get_item(db, current_user.tenant_id, item_id)


@router.patch(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Actualizar ítem de inventario",
    description="Actualiza cantidad, categoría u otros datos de un ítem de inventario.",
)
async def update_item(
    request: Request,
    item_id: uuid.UUID,
    data: InventoryItemUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    item = await inventory_service.update_item(db, current_user.tenant_id, item_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="inventory_item.updated",
        resource="inventory_item",
        resource_id=item.id,
        details=data.model_dump(exclude_unset=True, mode="json"),
        ip_address=client_ip(request),
    )
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar ítem de inventario",
    description="Elimina un ítem de inventario del gimnasio.",
)
async def delete_item(
    request: Request,
    item_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    await inventory_service.delete_item(db, current_user.tenant_id, item_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="inventory_item.deleted",
        resource="inventory_item",
        resource_id=item_id,
        ip_address=client_ip(request),
    )
