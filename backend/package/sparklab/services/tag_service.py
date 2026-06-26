from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.repositories.tag_repository import TagRepository

PRESET_TAGS = [
    ("小红书", "platform", 1),
    ("抖音", "platform", 2),
    ("微信", "platform", 3),
    ("公众号", "platform", 4),
    ("种草", "content_type", 1),
    ("干货", "content_type", 2),
    ("直播脚本", "content_type", 3),
    ("电商", "industry", 1),
    ("教育", "industry", 2),
    ("餐饮", "industry", 3),
]


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TagRepository(db)

    async def ensure_presets(self) -> None:
        for name, category, sort_order in PRESET_TAGS:
            existing = await self.repo.get_by_name_and_category(name, category)
            if existing is None:
                await self.repo.create(name, category, sort_order)
        await self.db.commit()

    async def list_tags(self, category: str | None = None) -> tuple[list, int]:
        return await self.repo.list_all(category)

    async def create_tag(self, name: str, category: str, sort_order: int = 0):
        existing = await self.repo.get_by_name_and_category(name, category)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该分类下已存在同名标签",
            )
        tag = await self.repo.create(name, category, sort_order)
        await self.db.commit()
        return tag

    async def update_tag(self, tag_id: int, name: str | None = None, sort_order: int | None = None):
        tag = await self.repo.update(tag_id, name, sort_order)
        if tag is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
        await self.db.commit()
        return tag

    async def delete_tag(self, tag_id: int) -> None:
        deleted = await self.repo.delete(tag_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
        await self.db.commit()

    async def list_by_category_grouped(self) -> dict[str, list]:
        from sparklab.models.tag import TagCategory

        result = {}
        for cat in TagCategory:
            items, _ = await self.repo.list_all(cat.value)
            result[cat.value] = items
        return result
