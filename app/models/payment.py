import uuid
from enum import StrEnum

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class PaymentStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class PaymentProvider(StrEnum):
    mercadopago = "mercadopago"


class Payment(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    membership_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS")
    status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.pending, nullable=False)
    provider: Mapped[PaymentProvider] = mapped_column(
        default=PaymentProvider.mercadopago, nullable=False
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
