"""工作流 (Playbook) 数据访问层。

所有方法都是 async；只做 DB 操作，不做业务校验。"""
import json

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sparklab.models.playbook import Playbook, PlaybookStatus, PlaybookStep, PlaybookTag


class PlaybookRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, playbook_id: int) -> Playbook | None:
        result = await self.db.execute(
            select(Playbook)
            .where(Playbook.id == playbook_id)
            .options(
                selectinload(Playbook.tags),
                selectinload(Playbook.steps),
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        search: str | None = None,
        tag_id_groups: list[list[int]] | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "use_count",
    ) -> tuple[list[Playbook], int]:
        query = select(Playbook).options(
            selectinload(Playbook.tags),
            selectinload(Playbook.steps),
        )
        count_query = select(func.count(Playbook.id))

        if search:
            pattern = f"%{search}%"
            cond = Playbook.title.ilike(pattern) | Playbook.description.ilike(pattern)
            query = query.where(cond)
            count_query = count_query.where(cond)

        if status:
            query = query.where(Playbook.status == status)
            count_query = count_query.where(Playbook.status == status)

        # 标签筛选：组间 AND、组内 OR
        if tag_id_groups:
            for group in tag_id_groups:
                if not group:
                    continue
                exists_clause = (
                    select(PlaybookTag.playbook_id)
                    .where(
                        PlaybookTag.playbook_id == Playbook.id,
                        PlaybookTag.tag_id.in_(group),
                    )
                    .exists()
                )
                query = query.where(exists_clause)
                count_query = count_query.where(exists_clause)

        if sort_by == "newest":
            query = query.order_by(Playbook.created_at.desc())
        else:
            query = query.order_by(Playbook.use_count.desc(), Playbook.created_at.desc())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create(
        self,
        *,
        title: str,
        description: str,
        content: str,
        variable_hints: dict | None,
        steps: list[dict],
        status: str,
        creator_id: int | None,
        tag_ids: list[int] | None,
    ) -> Playbook:
        playbook = Playbook(
            title=title,
            description=description,
            content=content,
            variable_hints=json.dumps(variable_hints, ensure_ascii=False) if variable_hints else None,
            status=PlaybookStatus(status),
            creator_id=creator_id,
        )
        self.db.add(playbook)
        await self.db.flush()

        for step in steps:
            self.db.add(
                PlaybookStep(
                    playbook_id=playbook.id,
                    step_order=step["step_order"],
                    name=step["name"],
                    description=step.get("description"),
                    content=step.get("content", ""),
                )
            )
        await self.db.flush()

        if tag_ids:
            for tid in tag_ids:
                self.db.add(PlaybookTag(playbook_id=playbook.id, tag_id=tid))
            await self.db.flush()

        return playbook

    async def update(
        self,
        playbook_id: int,
        **kwargs,
    ) -> Playbook | None:
        playbook = await self.db.get(Playbook, playbook_id)
        if not playbook:
            return None

        tag_ids = kwargs.pop("tag_ids", _SENTINEL)
        variable_hints = kwargs.pop("variable_hints", _SENTINEL)
        status = kwargs.pop("status", _SENTINEL)
        steps = kwargs.pop("steps", _SENTINEL)

        for key, value in kwargs.items():
            if value is not None:
                setattr(playbook, key, value)

        if variable_hints is not _SENTINEL:
            playbook.variable_hints = (
                json.dumps(variable_hints, ensure_ascii=False) if variable_hints else None
            )
        if status is not _SENTINEL:
            playbook.status = PlaybookStatus(status)

        await self.db.flush()

        if steps is not _SENTINEL:
            # 整组替换
            await self.db.execute(
                delete(PlaybookStep).where(PlaybookStep.playbook_id == playbook_id)
            )
            for s in steps:
                self.db.add(
                    PlaybookStep(
                        playbook_id=playbook_id,
                        step_order=s["step_order"],
                        name=s["name"],
                        description=s.get("description"),
                        content=s.get("content", ""),
                    )
                )
            await self.db.flush()

        if tag_ids is not _SENTINEL:
            await self.db.execute(
                delete(PlaybookTag).where(PlaybookTag.playbook_id == playbook_id)
            )
            for tid in tag_ids:
                self.db.add(PlaybookTag(playbook_id=playbook_id, tag_id=tid))
            await self.db.flush()

        return playbook

    async def update_status(self, playbook_id: int, status: str) -> Playbook | None:
        playbook = await self.db.get(Playbook, playbook_id)
        if not playbook:
            return None
        playbook.status = PlaybookStatus(status)
        await self.db.flush()
        return playbook

    async def increment_use_count(self, playbook_id: int) -> None:
        await self.db.execute(
            update(Playbook)
            .where(Playbook.id == playbook_id)
            .values(use_count=Playbook.use_count + 1)
        )
        await self.db.flush()

    async def delete(self, playbook_id: int) -> bool:
        """软删除：status=archived。"""
        playbook = await self.db.get(Playbook, playbook_id)
        if not playbook:
            return False
        playbook.status = PlaybookStatus.ARCHIVED
        await self.db.flush()
        return True

    async def hard_delete(self, playbook_id: int) -> bool:
        """物理删除：CASCADE 清 playbook_steps / playbook_tags。"""
        playbook = await self.db.get(Playbook, playbook_id)
        if not playbook:
            return False
        await self.db.delete(playbook)
        await self.db.flush()
        return True


# 用来在 update() 里区分「没传 steps/tag_ids」(sentinel) vs 「传了空列表」(要清空)
_SENTINEL = object()
