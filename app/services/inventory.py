import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem
from app.repositories.base import TenantScopedRepository
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate


async def create_item(
    db: AsyncSession, tenant_id: uuid.UUID, data: InventoryItemCreate
) -> InventoryItem:
    repo = TenantScopedRepository(db, InventoryItem, tenant_id)
    item = repo.add(InventoryItem(**data.model_dump()))
    await db.commit()
    await db.refresh(item)
    return item


async def list_items(
    db: AsyncSession, tenant_id: uuid.UUID, page: int, size: int
) -> tuple[list[InventoryItem], int]:
    conditions = [InventoryItem.tenant_id == tenant_id]
    total = await db.scalar(select(func.count()).select_from(InventoryItem).where(*conditions)) or 0
    stmt = (
        select(InventoryItem)
        .where(*conditions)
        .order_by(InventoryItem.name)
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_item(db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID) -> InventoryItem:
    repo = TenantScopedRepository(db, InventoryItem, tenant_id)
    item = await repo.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "detail": "Ítem de inventario no encontrado",
                "code": "INVENTORY_ITEM_NOT_FOUND",
            },
        )
    return item


async def update_item(
    db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID, data: InventoryItemUpdate
) -> InventoryItem:
    item = await get_item(db, tenant_id, item_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, tenant_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = await get_item(db, tenant_id, item_id)
    await db.delete(item)
    await db.commit()
