"""数据看板业务编排层。

所有计算逻辑集中在 Service；Repository 只负责 SQL。Service 把 range 字符串
解析为「起始时间」并分发给不同的查询路径（累计 vs 区间）。
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.repositories.dashboard_repository import (
    DashboardRepository,
    range_days,
    range_to_since,
)
from sparklab.schemas.dashboard import (
    ActivationCodeStats,
    DashboardStatsResponse,
    RecentActivityResponse,
    TopPlaybookItem,
    TopPlaybookResponse,
    TopTemplateItem,
    TopTemplateResponse,
    UsesTrendPoint,
)
from sparklab.schemas.template import TagInfo


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = DashboardRepository(db)

    @staticmethod
    def _normalize_range(range_str: str | None) -> str:
        """校验并归一化 range 参数。非法值 → 400。"""
        if range_str is None or range_str == "":
            return "all"
        if range_str in {"7d", "30d", "all"}:
            return range_str
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的 range 参数：{range_str}（可选：7d / 30d / all）",
        )

    # ------------------------------------------------------------------
    # 核心指标
    # ------------------------------------------------------------------

    async def get_stats(self, range_str: str | None) -> DashboardStatsResponse:
        range_normalized = self._normalize_range(range_str)
        since = range_to_since(range_normalized)

        templates_published = await self.repo.count_templates_published()
        playbooks_published = await self.repo.count_playbooks_published()
        users_total = await self.repo.count_users_total()
        ac_stats = await self.repo.activation_code_stats()

        if since is None:
            # all 模式：累计 use_count + 全部 favorites
            total_uses = await self.repo.sum_templates_use_count() + await self.repo.sum_playbooks_use_count()
            total_favorites = await self.repo.count_favorites_total()
            users_new = 0
            uses_trend: list[UsesTrendPoint] = []
        else:
            total_uses = await self.repo.count_runs_in_range(since)
            total_favorites = await self.repo.count_favorites_in_range(since)
            users_new = await self.repo.count_users_in_range(since)
            days = range_days(range_normalized)
            raw_trend = await self.repo.uses_trend_in_range(since, days)
            uses_trend = [UsesTrendPoint(**point) for point in raw_trend]

        return DashboardStatsResponse(
            range=range_normalized,
            templates_published=templates_published,
            playbooks_published=playbooks_published,
            total_uses=total_uses,
            total_favorites=total_favorites,
            users_total=users_total,
            users_new=users_new,
            activation_codes=ActivationCodeStats(**ac_stats),
            uses_trend=uses_trend,
        )

    # ------------------------------------------------------------------
    # 排行榜
    # ------------------------------------------------------------------

    async def get_top_templates(self, range_str: str | None, limit: int) -> TopTemplateResponse:
        range_normalized = self._normalize_range(range_str)
        since = range_to_since(range_normalized)

        if since is None:
            templates = await self.repo.top_templates_all(limit)
            items = [
                TopTemplateItem(
                    id=t.id,
                    title=t.title,
                    description=t.description,
                    use_count=t.use_count,
                    tags=[TagInfo.model_validate(tag) for tag in (t.tags or [])],
                )
                for t in templates
            ]
        else:
            rows = await self.repo.top_templates_in_range(since, limit)
            items = [
                TopTemplateItem(
                    id=t.id,
                    title=t.title,
                    description=t.description,
                    use_count=runs,
                    tags=[TagInfo.model_validate(tag) for tag in (t.tags or [])],
                )
                for t, runs in rows
            ]

        return TopTemplateResponse(items=items, range=range_normalized)

    async def get_top_playbooks(self, range_str: str | None, limit: int) -> TopPlaybookResponse:
        range_normalized = self._normalize_range(range_str)
        since = range_to_since(range_normalized)

        if since is None:
            playbooks = await self.repo.top_playbooks_all(limit)
            items = [
                TopPlaybookItem(
                    id=p.id,
                    title=p.title,
                    description=p.description,
                    use_count=p.use_count,
                    steps_count=len(p.steps or []),
                    tags=[TagInfo.model_validate(tag) for tag in (p.tags or [])],
                )
                for p in playbooks
            ]
        else:
            rows = await self.repo.top_playbooks_in_range(since, limit)
            items = [
                TopPlaybookItem(
                    id=p.id,
                    title=p.title,
                    description=p.description,
                    use_count=runs,
                    steps_count=len(p.steps or []),
                    tags=[TagInfo.model_validate(tag) for tag in (p.tags or [])],
                )
                for p, runs in rows
            ]

        return TopPlaybookResponse(items=items, range=range_normalized)

    # ------------------------------------------------------------------
    # 近期动态
    # ------------------------------------------------------------------

    async def get_recent_activity(self, limit: int) -> RecentActivityResponse:
        raw = await self.repo.recent_activity(limit)
        return RecentActivityResponse.model_validate({"items": raw})
