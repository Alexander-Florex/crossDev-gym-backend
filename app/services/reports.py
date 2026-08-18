import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.booking import Booking, BookingStatus
from app.models.class_ import Class
from app.models.membership import Membership, MembershipStatus
from app.models.user import User, UserRole
from app.schemas.report import OverviewReport


async def build_overview(db: AsyncSession, tenant_id: uuid.UUID) -> OverviewReport:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    active_students = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.student,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
    ) or 0

    active_trainers = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.tenant_id == tenant_id,
            User.role == UserRole.trainer,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
    ) or 0

    memberships_active = await db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.tenant_id == tenant_id, Membership.status == MembershipStatus.active)
    ) or 0

    memberships_expired = await db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(Membership.tenant_id == tenant_id, Membership.status == MembershipStatus.expired)
    ) or 0

    memberships_suspended = await db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(
            Membership.tenant_id == tenant_id, Membership.status == MembershipStatus.suspended
        )
    ) or 0

    active_classes = await db.scalar(
        select(func.count())
        .select_from(Class)
        .where(Class.tenant_id == tenant_id, Class.is_active.is_(True))
    ) or 0

    bookings_today = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.status == BookingStatus.confirmed,
            Booking.booked_at >= today_start,
            Booking.booked_at < today_end,
        )
    ) or 0

    attendance_today = await db.scalar(
        select(func.count())
        .select_from(Attendance)
        .where(
            Attendance.tenant_id == tenant_id,
            Attendance.checked_in_at >= today_start,
            Attendance.checked_in_at < today_end,
        )
    ) or 0

    return OverviewReport(
        active_students=active_students,
        active_trainers=active_trainers,
        memberships_active=memberships_active,
        memberships_expired=memberships_expired,
        memberships_suspended=memberships_suspended,
        active_classes=active_classes,
        bookings_today=bookings_today,
        attendance_today=attendance_today,
    )
