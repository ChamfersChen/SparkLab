"""工作流路由（用户端）。

普通用户和管理员都可调用：
- GET    /api/playbooks              → 工作流列表（搜索+标签+分页+排序，仅 published）
- GET    /api/playbooks/{id}         → 工作流详情（可见性受 playbook service 控制）
- POST   /api/playbooks/{id}/use     → use_count +1
- POST   /api/playbooks/{id}/run    → 运行工作流，返回完整渲染的 prompt

复用 template_router._parse_tag_id_groups 处理 tag_ids 字符串。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.routers.template_router import _parse_tag_id_groups
from server.utils.auth_middleware import get_db, get_required_user
from sparklab.schemas.playbook import (
    PlaybookListResponse,
    PlaybookResponse,
    PlaybookRunRequest,
    PlaybookRunResponse,
)
from sparklab.services.playbook_service import PlaybookService


playbook = APIRouter(prefix="/playbooks", tags=["工作流"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> PlaybookService:
    return PlaybookService(db)


@playbook.get("", response_model=PlaybookListResponse)
async def list_playbooks(
    search: str | None = Query(None, description="搜索标题/描述"),
    tag_ids: str | None = Query(
        None,
        description="标签筛选: 分号分组,逗号分隔成员。组间 AND、组内 OR,例如 '1,2;3'",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("use_count", description="排序：use_count / newest"),
    user=Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    items, total = await service.list_playbooks(
        search=search,
        tag_id_groups=_parse_tag_id_groups(tag_ids),
        status="published",
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return PlaybookListResponse(
        items=[PlaybookResponse.model_validate(p) for p in items],
        total=total,
    )


@playbook.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: int,
    user=Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    playbook_obj = await service.get_playbook_for_user(playbook_id, user)
    if playbook_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作流不存在",
        )
    return PlaybookResponse.model_validate(playbook_obj)


@playbook.post("/{playbook_id}/use")
async def increment_use_count(
    playbook_id: int,
    user=Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    await service.increment_use_count(playbook_id)
    return {"message": "ok"}


@playbook.post("/{playbook_id}/run", response_model=PlaybookRunResponse)
async def run_playbook(
    playbook_id: int,
    body: PlaybookRunRequest,
    user=Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    return await service.run_playbook(
        playbook_id,
        user,
        body.form_values,
        body.step_outputs,
    )
