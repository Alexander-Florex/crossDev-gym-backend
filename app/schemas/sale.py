import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.sale import PaymentMethod, SaleStatus, SaleType


class SaleItemInput(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)


class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class ProductSaleCreate(BaseModel):
    items: list[SaleItemInput] = Field(min_length=1)
    payment_method: PaymentMethod
    user_id: uuid.UUID | None = None
    notes: str | None = None


class MembershipPaymentCreate(BaseModel):
    payment_method: PaymentMethod
    notes: str | None = None


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    sale_type: SaleType
    status: SaleStatus
    payment_method: PaymentMethod
    amount: float
    user_id: uuid.UUID | None
    membership_id: uuid.UUID | None
    registered_by_id: uuid.UUID
    notes: str | None
    created_at: datetime
    items: list[SaleItemResponse] = []
