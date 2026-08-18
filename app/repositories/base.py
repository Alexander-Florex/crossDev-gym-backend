import uuid

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base


class TenantScopedRepository[ModelT: Base]:
    """Query helper that always scopes reads/writes to a single tenant_id.

    Every model used here MUST carry a tenant_id column (via TenantMixin) —
    this is the one place allowed to touch tenant_id filtering directly.
    """

    def __init__(self, db: AsyncSession, model: type[ModelT], tenant_id: uuid.UUID):
        self.db = db
        self.model = model
        self.tenant_id = tenant_id

    async def list(self, *conditions: ColumnElement[bool]) -> list[ModelT]:
        stmt = select(self.model).where(self.model.tenant_id == self.tenant_id, *conditions)
        result = await self.db.scalars(stmt)
        return list(result.all())

    async def get(self, obj_id: uuid.UUID) -> ModelT | None:
        obj = await self.db.get(self.model, obj_id)
        if obj is None or obj.tenant_id != self.tenant_id:
            return None
        return obj

    def add(self, obj: ModelT) -> ModelT:
        obj.tenant_id = self.tenant_id
        self.db.add(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
