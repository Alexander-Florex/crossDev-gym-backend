import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.membership import MembershipPeriod, MembershipStatus


class MembershipCreate(BaseModel):
    user_id: uuid.UUID
    plan_name: str
    period: MembershipPeriod = MembershipPeriod.monthly
    start_date: date
    end_date: date
    price: float


class MembershipUpdate(BaseModel):
    plan_name: str | None = None
    period: MembershipPeriod | None = None
    status: MembershipStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    price: float | None = None


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    plan_name: str
    period: MembershipPeriod
    status: MembershipStatus
    start_date: date
    end_date: date
    price: float
