"""收藏数据访问层。"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.favorite import Favorite, FavoriteTargetType
from sparklab.models.playbook import Playbook
from sparklab.models.template import Template


class FavoriteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_and_target(
        self, user_id: int, target_type: FavoriteTargetType, target_id: int
    ) -> Favorite | None:
        result = await self.db.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.target_type == target_type,
                Favorite.target_id == target_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        *,
        target_type: FavoriteTargetType | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        """返回用户收藏列表,每项包含收藏元数据 + 目标标题/描述。"""
        base = select(Favorite).where(Favorite.user_id == user_id)
        if target_type:
            base = base.where(Favorite.target_type == target_type)
        base = base.order_by(Favorite.created_at.desc())

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        result = await self.db.execute(base.offset(offset).limit(limit))
        favorites = list(result.scalars().all())

        if not favorites:
            return [], total

        items: list[dict] = []
        # 按类型分组批量查询,减少 SQL 次数
        template_ids = [f.target_id for f in favorites if f.target_type == FavoriteTargetType.TEMPLATE]
        playbook_ids = [f.target_id for f in favorites if f.target_type == FavoriteTargetType.PLAYBOOK]

        template_map: dict[int, Template] = {}
        playbook_map: dict[int, Playbook] = {}

        if template_ids:
            tpl_result = await self.db.execute(select(Template).where(Template.id.in_(template_ids)))
            template_map = {t.id: t for t in tpl_result.scalars().all()}

        if playbook_ids:
            pb_result = await self.db.execute(select(Playbook).where(Playbook.id.in_(playbook_ids)))
            playbook_map = {p.id: p for p in pb_result.scalars().all()}

        for fav in favorites:
            if fav.target_type == FavoriteTargetType.TEMPLATE:
                tpl = template_map.get(fav.target_id)
                items.append(
                    {
                        "id": fav.id,
                        "target_type": fav.target_type.value,
                        "target_id": fav.target_id,
                        "title": tpl.title if tpl else "",
                        "description": tpl.description if tpl else "",
                        "created_at": fav.created_at,
                    }
                )
            else:
                pb = playbook_map.get(fav.target_id)
                items.append(
                    {
                        "id": fav.id,
                        "target_type": fav.target_type.value,
                        "target_id": fav.target_id,
                        "title": pb.title if pb else "",
                        "description": pb.description if pb else "",
                        "created_at": fav.created_at,
                    }
                )

        return items, total

    async def create(self, user_id: int, target_type: FavoriteTargetType, target_id: int) -> Favorite:
        fav = Favorite(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
        )
        self.db.add(fav)
        await self.db.flush()
        return fav

    async def delete(self, user_id: int, target_type: FavoriteTargetType, target_id: int) -> bool:
        result = await self.db.execute(
            delete(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.target_type == target_type,
                Favorite.target_id == target_id,
            )
        )
        return result.rowcount > 0
