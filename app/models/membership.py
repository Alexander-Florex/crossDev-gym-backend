import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TenantMixin, UUIDPKMixin


class MembershipStatus(StrEnum):
    active = "active"
    expired = "expired"
    suspended = "suspended"


class Membership(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        default=MembershipStatus.active, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
