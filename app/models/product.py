from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Product(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    """Ítems individuales para la venta (agua, Monster, creatina, proteína, etc.).

    Tiene su propio stock; al venderse (ver Sale/SaleItem) se descuenta automáticamente.
    """

    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
