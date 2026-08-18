import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TenantMixin, UUIDPKMixin, utcnow


class BookingStatus(StrEnum):
    confirmed = "confirmed"
    cancelled = "cancelled"


class Booking(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "bookings"

    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[BookingStatus] = mapped_column(default=BookingStatus.confirmed, nullable=False)
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
