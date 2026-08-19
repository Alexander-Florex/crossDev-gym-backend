import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.inventory import InventoryCategory


class InventoryItemCreate(BaseModel):
    name: str
    category: InventoryCategory = InventoryCategory.equipment
    quantity: int = 0
    unit: str | None = None
    min_stock: int | None = None
    notes: str | None = None


class InventoryItemUpdate(BaseModel):
    name: str | None = None
    category: InventoryCategory | None = None
    quantity: int | None = None
    unit: str | None = None
    min_stock: int | None = None
    notes: str | None = None
    is_active: bool | None = None


class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    category: InventoryCategory
    quantity: int
    unit: str | None
    min_stock: int | None
    notes: str | None
    is_active: bool
    created_at: datetime
