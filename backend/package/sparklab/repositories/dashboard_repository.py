"""数据看板数据访问层。

所有方法都是只读聚合查询，不修改任何业务表。Repository 不抛 HTTPException，
由 Service 层负责把 `None` / 异常转换成 HTTP 响应。
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import String, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sparklab.models.activation_code import ActivationCode, ActivationCodeStatus
from sparklab.models.favorite import Favorite
from sparklab.models.playbook import Playbook, PlaybookRun, PlaybookStatus
from sparklab.models.template import Template, TemplateRun, TemplateStatus
from sparklab.models.user import User

DashboardRangeStr = Literal["7d", "30d", "all"]

# range → 区间天数（用于趋势图按日填充）。all 模式无趋势数据。
_RANGE_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "all": 0}


def range_to_since(range_str: str) -> datetime | None:
    """把 range 字符串解析为「起始时间」。

    - `all` → None（不做时间过滤）
    - `7d` → now - 7 days
    - `30d` → now - 30 days
    - 其它 → 抛 ValueError（由 Service 层映射为 400）
    """
    if range_str not in _RANGE_DAYS:
        raise ValueError(f"Invalid range: {range_str}")
    if range_str == "all":
        return None
    return datetime.now(UTC) - timedelta(days=_RANGE_DAYS[range_str])


def range_days(range_str: str) -> int:
    """返回 range 对应的天数（用于趋势图按日补 0）。all 模式返回 0。"""
    return _RANGE_DAYS.get(range_str, 0)


class DashboardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 核心计数
    # ------------------------------------------------------------------

    async def count_templates_published(self) -> int:
        result = await self.db.execute(
            select(func.count(Template.id)).where(Template.status == TemplateStatus.PUBLISHED)
        )
        return result.scalar() or 0

    async def count_playbooks_published(self) -> int:
        result = await self.db.execute(
            select(func.count(Playbook.id)).where(Playbook.status == PlaybookStatus.PUBLISHED)
        )
        return result.scalar() or 0

    async def sum_templates_use_count(self) -> int:
        result = await self.db.execute(select(func.coalesce(func.sum(Template.use_count), 0)))
        return int(result.scalar() or 0)

    async def sum_playbooks_use_count(self) -> int:
        result = await self.db.execute(select(func.coalesce(func.sum(Playbook.use_count), 0)))
        return int(result.scalar() or 0)

    async def count_runs_in_range(self, since: datetime) -> int:
        """区间内：模板运行 + 工作流运行的总行数。"""
        tpl_runs = await self.db.execute(select(func.count(TemplateRun.id)).where(TemplateRun.created_at >= since))
        pb_runs = await self.db.execute(select(func.count(PlaybookRun.id)).where(PlaybookRun.created_at >= since))
        return (tpl_runs.scalar() or 0) + (pb_runs.scalar() or 0)

    async def count_favorites_total(self) -> int:
        result = await self.db.execute(select(func.count(Favorite.id)))
        return result.scalar() or 0

    async def count_favorites_in_range(self, since: datetime) -> int:
        result = await self.db.execute(select(func.count(Favorite.id)).where(Favorite.created_at >= since))
        return result.scalar() or 0

    async def count_users_total(self) -> int:
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar() or 0

    async def count_users_in_range(self, since: datetime) -> int:
        result = await self.db.execute(select(func.count(User.id)).where(User.created_at >= since))
        return result.scalar() or 0

    async def activation_code_stats(self) -> dict:
        """按 status 计数激活码，返回 {total, unused, used, disabled}。"""
        result = await self.db.execute(
            select(ActivationCode.status, func.count(ActivationCode.id)).group_by(ActivationCode.status)
        )
        counts = {status.value: 0 for status in ActivationCodeStatus}
        for status_value, count in result.all():
            counts[status_value] = count
        total = sum(counts.values())
        return {
            "total": total,
            "unused": counts[ActivationCodeStatus.UNUSED.value],
            "used": counts[ActivationCodeStatus.USED.value],
            "disabled": counts[ActivationCodeStatus.DISABLED.value],
        }

    # ------------------------------------------------------------------
    # 趋势：区间内每日使用次数
    # ------------------------------------------------------------------

    async def uses_trend_in_range(self, since: datetime, days: int) -> list[dict]:
        """按日聚合区间内 template_runs + playbook_runs 的行数。

        返回 `[{"date": "2026-07-01", "count": 5}, ...]`，按日期升序；
        区间内空缺的日期补 0，方便前端 ECharts 直接画线不断点。
        """
        tpl_by_day = (
            select(
                func.date(TemplateRun.created_at).label("day"),
                func.count(TemplateRun.id).label("n"),
            )
            .where(TemplateRun.created_at >= since)
            .group_by(func.date(TemplateRun.created_at))
        )
        pb_by_day = (
            select(
                func.date(PlaybookRun.created_at).label("day"),
                func.count(PlaybookRun.id).label("n"),
            )
            .where(PlaybookRun.created_at >= since)
            .group_by(func.date(PlaybookRun.created_at))
        )

        merged: dict[str, int] = {}
        for day, n in (await self.db.execute(tpl_by_day)).all():
            merged[str(day)] = merged.get(str(day), 0) + int(n or 0)
        for day, n in (await self.db.execute(pb_by_day)).all():
            merged[str(day)] = merged.get(str(day), 0) + int(n or 0)

        result = []
        start_date = since.date()
        for i in range(days):
            d = start_date + timedelta(days=i)
            key = d.isoformat()
            result.append({"date": key, "count": merged.get(key, 0)})
        return result

    # ------------------------------------------------------------------
    # 排行榜
    # ------------------------------------------------------------------

    async def top_templates_all(self, limit: int) -> list[Template]:
        """累计 Top N：按 templates.use_count 排序。"""
        result = await self.db.execute(
            select(Template)
            .options(selectinload(Template.tags))
            .order_by(Template.use_count.desc(), Template.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def top_templates_in_range(self, since: datetime, limit: int) -> list[tuple[Template, int]]:
        """区间内 Top N：按 template_runs 行数排序。返回 (template, runs_count)。"""
        runs_subq = (
            select(
                TemplateRun.template_id.label("tid"),
                func.count(TemplateRun.id).label("runs"),
            )
            .where(TemplateRun.created_at >= since)
            .group_by(TemplateRun.template_id)
            .subquery()
        )
        result = await self.db.execute(
            select(Template, runs_subq.c.runs)
            .options(selectinload(Template.tags))
            .join(runs_subq, Template.id == runs_subq.c.tid)
            .order_by(runs_subq.c.runs.desc(), Template.created_at.desc())
            .limit(limit)
        )
        return [(row[0], int(row[1] or 0)) for row in result.all()]

    async def top_playbooks_all(self, limit: int) -> list[Playbook]:
        result = await self.db.execute(
            select(Playbook)
            .options(selectinload(Playbook.tags), selectinload(Playbook.steps))
            .order_by(Playbook.use_count.desc(), Playbook.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def top_playbooks_in_range(self, since: datetime, limit: int) -> list[tuple[Playbook, int]]:
        runs_subq = (
            select(
                PlaybookRun.playbook_id.label("pid"),
                func.count(PlaybookRun.id).label("runs"),
            )
            .where(PlaybookRun.created_at >= since)
            .group_by(PlaybookRun.playbook_id)
            .subquery()
        )
        result = await self.db.execute(
            select(Playbook, runs_subq.c.runs)
            .options(selectinload(Playbook.tags), selectinload(Playbook.steps))
            .join(runs_subq, Playbook.id == runs_subq.c.pid)
            .order_by(runs_subq.c.runs.desc(), Playbook.created_at.desc())
            .limit(limit)
        )
        return [(row[0], int(row[1] or 0)) for row in result.all()]

    # ------------------------------------------------------------------
    # 近期发布动态
    # ------------------------------------------------------------------

    async def recent_activity(self, limit: int) -> list[dict]:
        """取最近 `limit` 条 published 状态模板/工作流，按 updated_at 降序。

        用 UNION ALL 合并两类资源；type 字段做资源类型标记。
        status 列在两个表里是不同的 enum 类型（template_status / playbook_status），
        UNION 要求类型一致，所以统一 cast 成 text。
        """
        tpl_q = select(
            literal_column("'template'").label("type"),
            Template.id.label("id"),
            Template.title.label("title"),
            Template.status.cast(String).label("status"),
            Template.creator_id.label("creator_id"),
            Template.updated_at.label("activity_at"),
        ).where(Template.status == TemplateStatus.PUBLISHED)
        pb_q = select(
            literal_column("'playbook'").label("type"),
            Playbook.id.label("id"),
            Playbook.title.label("title"),
            Playbook.status.cast(String).label("status"),
            Playbook.creator_id.label("creator_id"),
            Playbook.updated_at.label("activity_at"),
        ).where(Playbook.status == PlaybookStatus.PUBLISHED)
        union_q = tpl_q.union_all(pb_q).subquery()
        result = await self.db.execute(select(union_q).order_by(union_q.c.activity_at.desc()).limit(limit))
        rows = []
        for row in result.all():
            status_value = row.status.value if hasattr(row.status, "value") else row.status
            rows.append(
                {
                    "type": row.type,
                    "id": row.id,
                    "title": row.title,
                    "status": status_value,
                    "creator_id": row.creator_id,
                    "created_at": row.activity_at,
                }
            )
        return rows
