import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.tenant import PlanType


class TenantUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan_type: PlanType
    config: dict | None
    created_at: datetime
