import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User, UserRole
from app.schemas.attendance import AttendanceCreate, AttendanceResponse
from app.services import attendance as attendance_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def check_in(
    request: Request,
    data: AttendanceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    if current_user.role in (UserRole.admin, UserRole.trainer):
        if data.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"detail": "user_id es requerido", "code": "USER_ID_REQUIRED"},
            )
        target_user_id = data.user_id
    else:
        target_user_id = current_user.id

    attendance = await attendance_service.check_in(
        db, current_user.tenant_id, target_user_id, data.class_id
    )
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="attendance.checked_in",
        resource="attendance",
        resource_id=attendance.id,
        details={"target_user_id": str(target_user_id)},
        ip_address=client_ip(request),
    )
    return attendance


@router.get("", response_model=Page[AttendanceResponse])
async def list_attendance(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    class_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    user_id = current_user.id if current_user.role == UserRole.student else None
    items, total = await attendance_service.list_attendance(
        db, current_user.tenant_id, page, size, user_id, class_id
    )
    return build_page([AttendanceResponse.model_validate(a) for a in items], total, page, size)
