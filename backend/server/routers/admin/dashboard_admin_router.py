"""数据看板路由（管理员/超管）。

- GET /api/admin/dashboard/stats              → 核心指标 + 激活码分布 + 趋势
- GET /api/admin/dashboard/top-templates      → 模板 Top N
- GET /api/admin/dashboard/top-playbooks      → 工作流 Top N
- GET /api/admin/dashboard/recent-activity    → 近期发布动态
"""

from fastapi import APIRouter, Depends, Query
from sparklab.schemas.dashboard import (
    DashboardStatsResponse,
    RecentActivityResponse,
    TopPlaybookResponse,
    TopTemplateResponse,
)
from sparklab.services.dashboard_service import DashboardService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_current_admin, get_db

dashboard_admin = APIRouter(
    prefix="/dashboard",
    tags=["admin-dashboard"],
    dependencies=[Depends(get_current_admin)],
)


async def _get_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@dashboard_admin.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    range: str | None = Query(None, description="时间范围：7d / 30d / all（默认 all）"),
    service: DashboardService = Depends(_get_service),
):
    """核心指标卡：模板/工作流/用户/激活码/累计使用/累计收藏 + 趋势图数据。"""
    return await service.get_stats(range)


@dashboard_admin.get("/top-templates", response_model=TopTemplateResponse)
async def get_top_templates(
    range: str | None = Query(None, description="时间范围：7d / 30d / all（默认 all）"),
    limit: int = Query(10, ge=1, le=50, description="Top N，默认 10"),
    service: DashboardService = Depends(_get_service),
):
    """模板 Top N：按 use_count 排序。"""
    return await service.get_top_templates(range, limit)


@dashboard_admin.get("/top-playbooks", response_model=TopPlaybookResponse)
async def get_top_playbooks(
    range: str | None = Query(None, description="时间范围：7d / 30d / all（默认 all）"),
    limit: int = Query(10, ge=1, le=50, description="Top N，默认 10"),
    service: DashboardService = Depends(_get_service),
):
    """工作流 Top N：按 use_count 排序。"""
    return await service.get_top_playbooks(range, limit)


@dashboard_admin.get("/recent-activity", response_model=RecentActivityResponse)
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=50, description="最近 N 条动态，默认 20"),
    service: DashboardService = Depends(_get_service),
):
    """近期发布动态：published 状态的模板/工作流，按 updated_at 降序。"""
    return await service.get_recent_activity(limit)
