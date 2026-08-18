import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassCreate(BaseModel):
    name: str
    trainer_id: uuid.UUID
    schedule: datetime
    capacity: int


class ClassUpdate(BaseModel):
    name: str | None = None
    trainer_id: uuid.UUID | None = None
    schedule: datetime | None = None
    capacity: int | None = None
    is_active: bool | None = None


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    trainer_id: uuid.UUID
    schedule: datetime
    capacity: int
    is_active: bool
    available_spots: int | None = None
