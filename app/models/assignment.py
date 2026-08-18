import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import TenantMixin, UUIDPKMixin


class AssignmentStatus(StrEnum):
    active = "active"
    finished = "finished"


class TrainerStudentAssignment(UUIDPKMixin, TenantMixin, Base):
    __tablename__ = "trainer_student_assignments"

    trainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        default=AssignmentStatus.active, nullable=False
    )
