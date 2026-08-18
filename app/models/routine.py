import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TenantMixin, TimestampMixin, UUIDPKMixin


class Routine(UUIDPKMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "routines"

    trainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    exercises: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.order",
    )


class RoutineExercise(UUIDPKMixin, Base):
    __tablename__ = "routine_exercises"

    routine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("routines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    routine: Mapped[Routine] = relationship(back_populates="exercises")
