import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import TenantScopedRepository
from app.schemas.product import ProductCreate, ProductUpdate


async def create_product(db: AsyncSession, tenant_id: uuid.UUID, data: ProductCreate) -> Product:
    repo = TenantScopedRepository(db, Product, tenant_id)
    product = repo.add(Product(**data.model_dump()))
    await db.commit()
    await db.refresh(product)
    return product


async def list_products(
    db: AsyncSession, tenant_id: uuid.UUID, page: int, size: int, only_active: bool = False
) -> tuple[list[Product], int]:
    conditions = [Product.tenant_id == tenant_id]
    if only_active:
        conditions.append(Product.is_active.is_(True))

    total = await db.scalar(select(func.count()).select_from(Product).where(*conditions)) or 0
    stmt = (
        select(Product)
        .where(*conditions)
        .order_by(Product.name)
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_product(db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    repo = TenantScopedRepository(db, Product, tenant_id)
    product = await repo.get(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Producto no encontrado", "code": "PRODUCT_NOT_FOUND"},
        )
    return product


async def update_product(
    db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate
) -> Product:
    product = await get_product(db, tenant_id, product_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, tenant_id: uuid.UUID, product_id: uuid.UUID) -> None:
    product = await get_product(db, tenant_id, product_id)
    await db.delete(product)
    await db.commit()
