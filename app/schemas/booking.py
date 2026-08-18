import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    class_id: uuid.UUID
    student_id: uuid.UUID | None = None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    class_id: uuid.UUID
    student_id: uuid.UUID
    status: BookingStatus
    booked_at: datetime
