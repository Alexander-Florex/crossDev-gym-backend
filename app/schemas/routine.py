import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoutineExerciseCreate(BaseModel):
    exercise_name: str
    sets: int
    reps: int
    weight: float | None = None
    rest_seconds: int | None = None
    notes: str | None = None
    order: int = 0


class RoutineExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exercise_name: str
    sets: int
    reps: int
    weight: float | None
    rest_seconds: int | None
    notes: str | None
    order: int


class RoutineCreate(BaseModel):
    student_id: uuid.UUID
    trainer_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    exercises: list[RoutineExerciseCreate] = []


class RoutineUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    exercises: list[RoutineExerciseCreate] | None = None


class RoutineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    trainer_id: uuid.UUID
    student_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    exercises: list[RoutineExerciseResponse]
