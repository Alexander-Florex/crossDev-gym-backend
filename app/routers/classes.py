import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_role
from app.models.class_ import Class
from app.models.user import User, UserRole
from app.schemas.class_ import ClassCreate, ClassResponse, ClassUpdate
from app.services import classes as classes_service
from app.services.audit import client_ip, log_action
from app.utils.pagination import Page, build_page

router = APIRouter(prefix="/api/v1/classes", tags=["classes"])


async def _to_response(db: AsyncSession, gym_class: Class) -> ClassResponse:
    confirmed = await classes_service.count_confirmed_bookings(db, gym_class.id)
    response = ClassResponse.model_validate(gym_class)
    response.available_spots = max(gym_class.capacity - confirmed, 0)
    return response


@router.post("", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
async def create_class(
    request: Request,
    data: ClassCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    gym_class = await classes_service.create_class(db, current_user.tenant_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="class.created",
        resource="class",
        resource_id=gym_class.id,
        details={"name": gym_class.name, "trainer_id": str(gym_class.trainer_id)},
        ip_address=client_ip(request),
    )
    return await _to_response(db, gym_class)


@router.get("", response_model=Page[ClassResponse])
async def list_classes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    only_active: bool = True,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = await classes_service.list_classes(
        db, current_user.tenant_id, page, size, only_active
    )
    responses = [await _to_response(db, item) for item in items]
    return build_page(responses, total, page, size)


@router.get("/{class_id}", response_model=ClassResponse)
async def get_class(
    class_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    gym_class = await classes_service.get_class(db, current_user.tenant_id, class_id)
    return await _to_response(db, gym_class)


@router.patch("/{class_id}", response_model=ClassResponse)
async def update_class(
    request: Request,
    class_id: uuid.UUID,
    data: ClassUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    gym_class = await classes_service.update_class(db, current_user.tenant_id, class_id, data)
    await log_action(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="class.updated",
        resource="class",
        resource_id=gym_class.id,
        details=data.model_dump(exclude_unset=True, mode="json"),
        ip_address=client_ip(request),
    )
    return await _to_response(db, gym_class)
