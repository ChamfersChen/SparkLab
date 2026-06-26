from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.tag import Tag


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tag_id: int) -> Tag | None:
        return await self.db.get(Tag, tag_id)

    async def list_by_category(self, category: str | None = None) -> list[Tag]:
        query = select(Tag)
        if category:
            query = query.where(Tag.category == category)
        query = query.order_by(Tag.sort_order, Tag.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_all(self, category: str | None = None) -> tuple[list[Tag], int]:
        query = select(Tag)
        if category:
            query = query.where(Tag.category == category)
        count_result = await self.db.execute(query)
        total = len(count_result.scalars().all())
        query = query.order_by(Tag.sort_order, Tag.name)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_by_name_and_category(self, name: str, category: str) -> Tag | None:
        result = await self.db.execute(select(Tag).where(Tag.name == name, Tag.category == category))
        return result.scalar_one_or_none()

    async def create(self, name: str, category: str, sort_order: int = 0) -> Tag:
        tag = Tag(name=name, category=category, sort_order=sort_order)
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def update(self, tag_id: int, name: str | None = None, sort_order: int | None = None) -> Tag | None:
        tag = await self.db.get(Tag, tag_id)
        if tag:
            if name is not None:
                tag.name = name
            if sort_order is not None:
                tag.sort_order = sort_order
            await self.db.flush()
        return tag

    async def delete(self, tag_id: int) -> bool:
        tag = await self.db.get(Tag, tag_id)
        if tag:
            await self.db.delete(tag)
            await self.db.flush()
            return True
        return False

    async def count_by_category(self, category: str) -> int:
        result = await self.db.execute(select(Tag).where(Tag.category == category))
        return len(result.scalars().all())
