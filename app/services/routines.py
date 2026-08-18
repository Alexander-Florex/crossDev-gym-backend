import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.routine import Routine, RoutineExercise
from app.models.user import User, UserRole
from app.repositories.base import TenantScopedRepository
from app.schemas.routine import RoutineCreate, RoutineUpdate


async def _validate_role(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, role: UserRole, code: str
) -> User:
    user_repo = TenantScopedRepository(db, User, tenant_id)
    user = await user_repo.get(user_id)
    if user is None or user.is_deleted or user.role != role:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"detail": f"{user_id} no corresponde a un {role.value} válido", "code": code},
        )
    return user


async def create_routine(
    db: AsyncSession, tenant_id: uuid.UUID, trainer_id: uuid.UUID, data: RoutineCreate
) -> Routine:
    await _validate_role(db, tenant_id, data.student_id, UserRole.student, "INVALID_STUDENT")

    repo = TenantScopedRepository(db, Routine, tenant_id)
    routine = repo.add(
        Routine(
            trainer_id=trainer_id,
            student_id=data.student_id,
            name=data.name,
            description=data.description,
        )
    )
    for index, exercise in enumerate(data.exercises):
        routine.exercises.append(
            RoutineExercise(
                exercise_name=exercise.exercise_name,
                sets=exercise.sets,
                reps=exercise.reps,
                weight=exercise.weight,
                rest_seconds=exercise.rest_seconds,
                notes=exercise.notes,
                order=exercise.order or index,
            )
        )
    await db.commit()
    await db.refresh(routine)
    return await get_routine(db, tenant_id, routine.id)


async def list_routines(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    page: int,
    size: int,
    student_id: uuid.UUID | None = None,
    trainer_id: uuid.UUID | None = None,
) -> tuple[list[Routine], int]:
    conditions = [Routine.tenant_id == tenant_id]
    if student_id is not None:
        conditions.append(Routine.student_id == student_id)
    if trainer_id is not None:
        conditions.append(Routine.trainer_id == trainer_id)

    total = await db.scalar(select(func.count()).select_from(Routine).where(*conditions)) or 0
    stmt = (
        select(Routine)
        .where(*conditions)
        .options(selectinload(Routine.exercises))
        .order_by(Routine.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.scalars(stmt)
    return list(result.all()), total


async def get_routine(db: AsyncSession, tenant_id: uuid.UUID, routine_id: uuid.UUID) -> Routine:
    stmt = (
        select(Routine)
        .where(Routine.tenant_id == tenant_id, Routine.id == routine_id)
        .options(selectinload(Routine.exercises))
    )
    routine = await db.scalar(stmt)
    if routine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "Rutina no encontrada", "code": "ROUTINE_NOT_FOUND"},
        )
    return routine


async def update_routine(
    db: AsyncSession, tenant_id: uuid.UUID, routine_id: uuid.UUID, data: RoutineUpdate
) -> Routine:
    routine = await get_routine(db, tenant_id, routine_id)
    payload = data.model_dump(exclude_unset=True)
    exercises_payload = payload.pop("exercises", None)

    for field, value in payload.items():
        setattr(routine, field, value)

    if exercises_payload is not None:
        routine.exercises.clear()
        await db.flush()
        for index, exercise in enumerate(exercises_payload):
            routine.exercises.append(
                RoutineExercise(
                    exercise_name=exercise["exercise_name"],
                    sets=exercise["sets"],
                    reps=exercise["reps"],
                    weight=exercise.get("weight"),
                    rest_seconds=exercise.get("rest_seconds"),
                    notes=exercise.get("notes"),
                    order=exercise.get("order") or index,
                )
            )

    await db.commit()
    return await get_routine(db, tenant_id, routine_id)


async def delete_routine(db: AsyncSession, tenant_id: uuid.UUID, routine_id: uuid.UUID) -> None:
    routine = await get_routine(db, tenant_id, routine_id)
    await db.delete(routine)
    await db.commit()
