from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.schemas.report import OverviewReport
from app.services.reports import build_overview

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get(
    "/overview",
    response_model=OverviewReport,
    summary="Resumen del gimnasio",
    description="Contadores generales del gimnasio: alumnos y trainers activos, "
    "membresías por estado, clases activas, reservas y asistencias del día.",
)
async def overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
):
    return await build_overview(db, current_user.tenant_id)
