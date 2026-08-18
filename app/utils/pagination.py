import math

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


async def paginate(
    db: AsyncSession, stmt: Select, page: int, size: int
) -> tuple[list, int]:
    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.scalars(stmt.offset((page - 1) * size).limit(size))
    return list(result.all()), total


def build_page(items: list, total: int, page: int, size: int) -> dict:
    pages = math.ceil(total / size) if size else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}
