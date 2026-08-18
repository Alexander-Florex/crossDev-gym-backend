import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttendanceCreate(BaseModel):
    user_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    class_id: uuid.UUID | None
    checked_in_at: datetime
