from pydantic import BaseModel


class OverviewReport(BaseModel):
    active_students: int
    active_trainers: int
    memberships_active: int
    memberships_expired: int
    memberships_suspended: int
    active_classes: int
    bookings_today: int
    attendance_today: int
