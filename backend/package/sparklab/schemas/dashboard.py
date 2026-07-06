"""数据看板 Pydantic schemas。

所有响应模型都集中在此处，便于前后端契约对齐。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from sparklab.schemas.template import TagInfo

DashboardRange = Literal["7d", "30d", "all"]
"""时间范围筛选：7 天 / 30 天 / 全部。"""


class ActivationCodeStats(BaseModel):
    """激活码各状态计数。"""

    total: int = 0
    unused: int = 0
    used: int = 0
    disabled: int = 0


class UsesTrendPoint(BaseModel):
    """使用趋势数据点（按日聚合）。"""

    date: str
    count: int


class DashboardStatsResponse(BaseModel):
    """核心指标响应。

    字段语义：
    - `templates_published` / `playbooks_published`：始终为已发布数量的快照
    - `total_uses` / `total_favorites`：
        - `range=all` 时为累计值（`use_count` 字段求和 / `favorites` 总数）
        - `range=7d/30d` 时为区间内的 `runs` 表行数 / `favorites` 新增行数
    - `users_total`：用户总数（始终）
    - `users_new`：仅在 `range=7d/30d` 时返回；`range=all` 时为 0
    """

    range: DashboardRange
    templates_published: int
    playbooks_published: int
    total_uses: int
    total_favorites: int
    users_total: int
    users_new: int = 0
    activation_codes: ActivationCodeStats
    uses_trend: list[UsesTrendPoint] = Field(default_factory=list)


class TopTemplateItem(BaseModel):
    """模板排行榜单条。"""

    id: int
    title: str
    description: str
    use_count: int
    tags: list[TagInfo] = Field(default_factory=list)


class TopTemplateResponse(BaseModel):
    items: list[TopTemplateItem]
    range: DashboardRange


class TopPlaybookItem(BaseModel):
    """工作流排行榜单条。"""

    id: int
    title: str
    description: str
    use_count: int
    steps_count: int
    tags: list[TagInfo] = Field(default_factory=list)


class TopPlaybookResponse(BaseModel):
    items: list[TopPlaybookItem]
    range: DashboardRange


class RecentActivityItem(BaseModel):
    """近期发布动态单条。"""

    type: Literal["template", "playbook"]
    id: int
    title: str
    status: str
    creator_id: int | None = None
    created_at: datetime


class RecentActivityResponse(BaseModel):
    items: list[RecentActivityItem]
