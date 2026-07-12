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
        include_private: bool = False,
    ) -> tuple[list[Playbook], int]:
        """查询流程列表。

        Args:
            include_private: 是否包含私有流程。管理员查看时设为 True，
                           普通用户查看公开流程时设为 False（默认）。
        """
        query = select(Playbook).options(
            selectinload(Playbook.tags),
            selectinload(Playbook.steps),
        )
        count_query = select(func.count(Playbook.id))

        # 默认排除私有流程（除非明确包含）
        if not include_private:
            query = query.where(Playbook.is_private == False)  # noqa: E712
            count_query = count_query.where(Playbook.is_private == False)  # noqa: E712

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

    async def list_by_user(
        self,
        user_id: int,
        *,
        search: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "newest",
    ) -> tuple[list[Playbook], int]:
        """查询用户自己的流程列表（包含私有和公开的）。"""
        query = select(Playbook).options(
            selectinload(Playbook.tags),
            selectinload(Playbook.steps),
        )
        count_query = select(func.count(Playbook.id))

        # 只查当前用户的流程
        query = query.where(Playbook.creator_id == user_id)
        count_query = count_query.where(Playbook.creator_id == user_id)

        if search:
            pattern = f"%{search}%"
            cond = Playbook.title.ilike(pattern) | Playbook.description.ilike(pattern)
            query = query.where(cond)
            count_query = count_query.where(cond)

        if status:
            query = query.where(Playbook.status == status)
            count_query = count_query.where(Playbook.status == status)

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
        is_private: bool = False,
    ) -> Playbook:
        playbook = Playbook(
            title=title,
            description=description,
            content=content,
            variable_hints=json.dumps(variable_hints, ensure_ascii=False) if variable_hints else None,
            status=PlaybookStatus(status),
            creator_id=creator_id,
            is_private=is_private,
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


# ===========================================================================
# 工作流运行记录 (个人中心 / 我的运行记录)
# ===========================================================================

from sparklab.models.playbook import PlaybookRun, PlaybookRunStep  # noqa: E402  (同包,放这里便于读)


class PlaybookRunRepository:
    """工作流运行记录的 DB 访问层.

    list_by_user / get_by_id_for_user / delete 都按 user_id 隔离, 越权返回 None
    (路由层转为 404).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_with_steps(
        self,
        *,
        user_id: int,
        playbook_id: int,
        title: str | None,
        steps_data: list[dict],
        final_result: str | None = None,
        filled_prompts: list[str | None] | None = None,
    ) -> PlaybookRun:
        """插 playbook_runs + 批量插 playbook_run_steps, 单事务.

        steps_data 元素: {step_order, step_name, user_output, form_values, filled_prompt}
        - form_values 是 dict, 这里 json.dumps 存盘
        - user_output 为空字符串/None 时存 NULL
        - filled_prompts (可选) 与 steps_data 一一对应, server 现算的补充后 prompt
        - final_result (可选) 用户在三栏右栏填的"最终结果"
        """
        run = PlaybookRun(
            user_id=user_id,
            playbook_id=playbook_id,
            title=title,
            final_result=final_result,
        )
        self.db.add(run)
        await self.db.flush()

        for idx, s in enumerate(steps_data):
            fv = s.get("form_values") or {}
            filled = None
            if filled_prompts is not None and idx < len(filled_prompts):
                filled = filled_prompts[idx]
            self.db.add(
                PlaybookRunStep(
                    run_id=run.id,
                    step_order=int(s["step_order"]),
                    step_name=str(s.get("step_name") or ""),
                    user_output=(s.get("user_output") or None),
                    form_values_json=(
                        json.dumps(fv, ensure_ascii=False) if fv else None
                    ),
                    filled_prompt=filled,
                )
            )
        await self.db.flush()
        return run

    async def list_by_user(
        self,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PlaybookRun], int]:
        """按 created_at DESC 返回当前用户的运行记录 + total."""
        from sqlalchemy import func as sa_func

        count_q = select(sa_func.count(PlaybookRun.id)).where(PlaybookRun.user_id == user_id)
        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = (
            select(PlaybookRun)
            .where(PlaybookRun.user_id == user_id)
            .options(selectinload(PlaybookRun.steps))
            .order_by(PlaybookRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id_for_user(
        self,
        run_id: int,
        user_id: int,
    ) -> PlaybookRun | None:
        """按 id 查 + 校验归属. 越权 (run 不属于该 user) → None."""
        run = await self.db.get(PlaybookRun, run_id)
        if run is None:
            return None
        if run.user_id != user_id:
            return None
        # 显式 selectinload steps (get 不会自动 eager load relationship)
        result = await self.db.execute(
            select(PlaybookRun)
            .where(PlaybookRun.id == run_id)
            .options(selectinload(PlaybookRun.steps))
        )
        return result.scalar_one_or_none()

    async def delete(self, run_id: int, user_id: int) -> bool:
        """物理删除 (CASCADE 删 steps). 越权 → False."""
        run = await self.db.get(PlaybookRun, run_id)
        if run is None or run.user_id != user_id:
            return False
        await self.db.delete(run)
        await self.db.flush()
        return True


def summarize_run(run: PlaybookRun) -> dict:
    """把 PlaybookRun 拆成 summary dict (前端列表用)."""
    steps = list(run.steps or [])
    return {
        "id": run.id,
        "playbook_id": run.playbook_id,
        "playbook_title": run.playbook.title if run.playbook else "",
        "title": run.title,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "step_count": len(steps),
        "filled_step_count": sum(1 for s in steps if (s.user_output or "").strip()),
        "has_final_result": bool((run.final_result or "").strip()),
    }


def detail_run(run: PlaybookRun) -> dict:
    """把 PlaybookRun 拆成 detail dict (含 steps 详情, 前端详情/创建返回用)."""
    steps = list(run.steps or [])
    return {
        "id": run.id,
        "playbook_id": run.playbook_id,
        "playbook_title": run.playbook.title if run.playbook else "",
        "title": run.title,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "step_count": len(steps),
        "filled_step_count": sum(1 for s in steps if (s.user_output or "").strip()),
        "has_final_result": bool((run.final_result or "").strip()),
        "final_result": run.final_result,
        "steps": steps,
    }
