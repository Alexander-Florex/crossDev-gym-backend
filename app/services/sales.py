import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.membership import Membership
from app.models.product import Product
from app.models.sale import Sale, SaleItem, SaleStatus, SaleType
from app.repositories.base import TenantScopedRepository
from app.schemas.sale import MembershipPaymentCreate, ProductSaleCreate


async def _get_sale_with_items(db: AsyncSession, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
    stmt = (
        select(Sale)
        .where(Sale.id == sale_id, Sale.tenant_id == tenant_id)
        .options(selectinload(Sale.items))
    )
    sale = (await db.scalars(stmt)).first()
    if sale is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Venta no encontrada", "code": "SALE_NOT_FOUND"},
        )
    return sale


async def create_product_sale(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    registered_by_id: uuid.UUID,
    data: ProductSaleCreate,
) -> Sale:
    sale = Sale(
        tenant_id=tenant_id,
        sale_type=SaleType.product,
        payment_method=data.payment_method,
        amount=0,
        user_id=data.user_id,
        registered_by_id=registered_by_id,
        notes=data.notes,
    )

    total = 0.0
    for line in data.items:
        stmt = select(Product).where(Product.id == line.product_id).with_for_update()
        product = (await db.scalars(stmt)).first()
        if product is None or product.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"detail": "Producto no encontrado", "code": "PRODUCT_NOT_FOUND"},
            )
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "detail": "Producto no disponible para la venta",
                    "code": "PRODUCT_INACTIVE",
                },
            )
        if product.stock_quantity < line.quantity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "detail": f"Stock insuficiente de '{product.name}'",
                    "code": "PRODUCT_INSUFFICIENT_STOCK",
                },
            )

        product.stock_quantity -= line.quantity
        subtotal = float(product.price) * line.quantity
        total += subtotal
        sale.items.append(
            SaleItem(
                product_id=product.id,
                product_name=product.name,
                quantity=line.quantity,
                unit_price=product.price,
                subtotal=subtotal,
            )
        )

    sale.amount = total
    db.add(sale)
    await db.commit()
    return await _get_sale_with_items(db, tenant_id, sale.id)


async def create_membership_payment(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    registered_by_id: uuid.UUID,
    membership_id: uuid.UUID,
    data: MembershipPaymentCreate,
) -> Sale:
    membership_repo = TenantScopedRepository(db, Membership, tenant_id)
    membership = await membership_repo.get(membership_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Membresía no encontrada", "code": "MEMBERSHIP_NOT_FOUND"},
        )

    sale = Sale(
        tenant_id=tenant_id,
        sale_type=SaleType.membership,
        payment_method=data.payment_method,
        amount=membership.price,
        user_id=membership.user_id,
        membership_id=membership.id,
        registered_by_id=registered_by_id,
        notes=data.notes,
    )
    db.add(sale)
    await db.commit()
    return await _get_sale_with_items(db, tenant_id, sale.id)


async def list_sales(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int,
    size: int,
    sale_type: SaleType | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[list[Sale], int]:
    conditions = [Sale.tenant_id == tenant_id]
    if sale_type is not None:
        conditions.append(Sale.sale_type == sale_type)
    if user_id is not None:
        conditions.append(Sale.user_id == user_id)

    total = await db.scalar(select(func.count()).select_from(Sale).where(*conditions)) or 0
    stmt = (
        select(Sale)
        .where(*conditions)
        .options(selectinload(Sale.items))
        .order_by(Sale.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_sale(db: AsyncSession, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
    return await _get_sale_with_items(db, tenant_id, sale_id)


async def cancel_sale(db: AsyncSession, tenant_id: uuid.UUID, sale_id: uuid.UUID) -> Sale:
    sale = await get_sale(db, tenant_id, sale_id)
    if sale.status == SaleStatus.cancelled:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": "La venta ya está cancelada", "code": "SALE_ALREADY_CANCELLED"},
        )

    if sale.sale_type == SaleType.product:
        for item in sale.items:
            stmt = select(Product).where(Product.id == item.product_id).with_for_update()
            product = (await db.scalars(stmt)).first()
            if product is not None:
                product.stock_quantity += item.quantity

    sale.status = SaleStatus.cancelled
    await db.commit()
    return await _get_sale_with_items(db, tenant_id, sale.id)
