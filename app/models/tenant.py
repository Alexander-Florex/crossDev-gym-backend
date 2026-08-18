from enum import StrEnum

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class PlanType(StrEnum):
    basic = "basic"
    premium = "premium"


class Tenant(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    plan_type: Mapped[PlanType] = mapped_column(
        default=PlanType.basic, nullable=False
    )
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")  # noqa: F821
