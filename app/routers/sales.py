import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.sale import SaleType
from app.models.user import User, UserRole
from app.schemas.sale import MembershipPaymentCreate, ProductSaleCreate, SaleResponse
from app.services import sales as sales_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


@router.post(
    "/products",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar venta de productos",
    description="Registra la venta de uno o más productos y descuenta el stock automáticamente.",
)
async def create_product_sale(
    request: Request,
    data: ProductSaleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    sale = await sales_service.create_product_sale(
        db, current_user.tenant_id, current_user.id, data
    )
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="sale.product_created",
        resource="sale",
        resource_id=sale.id,
        details={"amount": str(sale.amount), "items": len(sale.items)},
        ip_address=client_ip(request),
    )
    return sale


@router.post(
    "/memberships/{membership_id}/pay",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Abonar membresía",
    description="Registra el pago (abono) del monto total de una membresía en caja.",
)
async def pay_membership(
    request: Request,
    membership_id: uuid.UUID,
    data: MembershipPaymentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    sale = await sales_service.create_membership_payment(
        db, current_user.tenant_id, current_user.id, membership_id, data
    )
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="sale.membership_paid",
        resource="sale",
        resource_id=sale.id,
        details={"amount": str(sale.amount), "membership_id": str(membership_id)},
        ip_address=client_ip(request),
    )
    return sale


@router.get(
    "",
    response_model=Page[SaleResponse],
    summary="Listar ventas",
    description=(
        "Lista paginada de movimientos de caja (ventas de productos y pagos de membresías)."
    ),
)
async def list_sales(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
    sale_type: SaleType | None = None,
    user_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    sales, total = await sales_service.list_sales(
        db, current_user.tenant_id, page, size, sale_type, user_id
    )
    return build_page([SaleResponse.model_validate(s) for s in sales], total, page, size)


@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
    summary="Obtener venta",
    description="Devuelve el detalle de un movimiento de caja por id.",
)
async def get_sale(
    sale_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.trainer))],
):
    return await sales_service.get_sale(db, current_user.tenant_id, sale_id)


@router.post(
    "/{sale_id}/cancel",
    response_model=SaleResponse,
    summary="Cancelar venta",
    description="Cancela un movimiento de caja; si era venta de productos, repone el stock.",
)
async def cancel_sale(
    request: Request,
    sale_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    sale = await sales_service.cancel_sale(db, current_user.tenant_id, sale_id)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="sale.cancelled",
        resource="sale",
        resource_id=sale.id,
        ip_address=client_ip(request),
    )
    return sale
