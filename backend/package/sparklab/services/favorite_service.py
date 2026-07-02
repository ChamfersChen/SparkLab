"""收藏业务逻辑层。"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.favorite import FavoriteTargetType
from sparklab.models.playbook import Playbook, PlaybookStatus
from sparklab.models.template import Template, TemplateStatus
from sparklab.repositories.favorite_repository import FavoriteRepository


class FavoriteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = FavoriteRepository(db)

    async def _validate_target(self, target_type: FavoriteTargetType, target_id: int) -> None:
        """校验目标存在且已发布。"""
        if target_type == FavoriteTargetType.TEMPLATE:
            result = await self.db.execute(
                __import__("sqlalchemy").select(Template).where(Template.id == target_id)
            )
            tpl = result.scalar_one_or_none()
            if not tpl:
                raise HTTPException(status_code=404, detail="模板不存在")
            if tpl.status != TemplateStatus.PUBLISHED:
                raise HTTPException(status_code=400, detail="该模板未发布,无法收藏")
        else:
            result = await self.db.execute(
                __import__("sqlalchemy").select(Playbook).where(Playbook.id == target_id)
            )
            pb = result.scalar_one_or_none()
            if not pb:
                raise HTTPException(status_code=404, detail="工作流不存在")
            if pb.status != PlaybookStatus.PUBLISHED:
                raise HTTPException(status_code=400, detail="该工作流未发布,无法收藏")

    async def toggle(self, user_id: int, target_type: FavoriteTargetType, target_id: int) -> dict:
        """切换收藏状态。返回 {favorited: bool, ...}。"""
        existing = await self.repo.get_by_user_and_target(user_id, target_type, target_id)
        if existing:
            await self.repo.delete(user_id, target_type, target_id)
            await self.db.commit()
            return {"favorited": False}

        await self._validate_target(target_type, target_id)
        await self.repo.create(user_id, target_type, target_id)
        await self.db.commit()
        return {"favorited": True}

    async def list_favorites(
        self,
        user_id: int,
        *,
        target_type: FavoriteTargetType | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict], int]:
        return await self.repo.list_by_user(
            user_id,
            target_type=target_type,
            offset=(page - 1) * page_size,
            limit=page_size,
        )

    async def check_favorited(
        self, user_id: int, target_type: FavoriteTargetType, target_id: int
    ) -> bool:
        fav = await self.repo.get_by_user_and_target(user_id, target_type, target_id)
        return fav is not None
