from enum import StrEnum

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class InventoryCategory(StrEnum):
    equipment = "equipment"
    consumable = "consumable"
    other = "other"


class InventoryItem(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    """Activos fijos y consumibles del gimnasio (sogas, mancuernas, bancas, packs de agua, etc.).

    No es vendible directamente; los ítems para la venta viven en Product.
    """

    __tablename__ = "inventory_items"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[InventoryCategory] = mapped_column(
        default=InventoryCategory.equipment, nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    min_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
