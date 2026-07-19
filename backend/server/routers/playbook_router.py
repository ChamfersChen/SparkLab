"""工作流路由（用户端）。

普通用户和管理员都可调用：
- GET    /api/playbooks              → 工作流列表（搜索+标签+分页+排序，仅 published）
- GET    /api/playbooks/runs         → 当前用户「我的运行记录」列表
- POST   /api/playbooks/runs         → 保存一次工作流运行结果
- GET    /api/playbooks/runs/{run_id} → 单条运行记录详情
- DELETE /api/playbooks/runs/{run_id} → 删除一条运行记录
- GET    /api/playbooks/{id}         → 工作流详情（可见性受 playbook service 控制）
- POST   /api/playbooks/{id}/use     → use_count +1
- POST   /api/playbooks/{id}/run    → 运行工作流，返回完整渲染的 prompt

注意: `runs` 字面量路径必须声明在 `{playbook_id}` 参数化路径之前,
否则 FastAPI 会把 "runs" 当 playbook_id 解析 (404).

复用 template_router._parse_tag_id_groups 处理 tag_ids 字符串。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.repositories.playbook_repository import detail_run
from sparklab.schemas.playbook import (
    PlaybookListResponse,
    PlaybookResponse,
    PlaybookRunCreateRequest,
    PlaybookRunDetail,
    PlaybookRunListResponse,
    PlaybookRunRequest,
    PlaybookRunResponse,
)
from sparklab.services.playbook_service import PlaybookRunService, PlaybookService
from sqlalchemy.ext.asyncio import AsyncSession

from server.routers.template_router import _parse_tag_id_groups
from server.utils.auth_middleware import get_db, get_required_user

playbook = APIRouter(prefix="/playbooks", tags=["工作流"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> PlaybookService:
    return PlaybookService(db)


async def _get_run_service(db: AsyncSession = Depends(get_db)) -> PlaybookRunService:
    return PlaybookRunService(db)


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


# ---------------------------------------------------------------------------
# 运行记录 (个人中心 / 我的运行记录)
# 必须在 {playbook_id} 路径之前声明, 否则会被参数化路径吞掉
# ---------------------------------------------------------------------------


@playbook.get("/runs", response_model=PlaybookRunListResponse)
async def list_my_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_required_user),
    run_service: PlaybookRunService = Depends(_get_run_service),
):
    """当前用户的运行记录列表, 按 created_at DESC."""
    items, total = await run_service.list_user_runs(
        user.id,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return PlaybookRunListResponse(items=items, total=total)


@playbook.post("/runs", response_model=PlaybookRunDetail, status_code=status.HTTP_201_CREATED)
async def create_run(
    body: PlaybookRunCreateRequest,
    user=Depends(get_required_user),
    run_service: PlaybookRunService = Depends(_get_run_service),
):
    """保存一次工作流运行结果. 至少需要粘回 1 个 step 的 AI 结果 OR 在右栏填最终结果."""
    steps_data = [
        {
            "step_order": s.step_order,
            "step_name": s.step_name,
            "user_output": s.user_output,
            "form_values": s.form_values,
        }
        for s in body.steps
    ]
    run = await run_service.create_run(
        user=user,
        playbook_id=body.playbook_id,
        title=body.title,
        steps_data=steps_data,
        final_result=body.final_result,
    )
    return detail_run(run)


@playbook.get("/runs/{run_id}", response_model=PlaybookRunDetail)
async def get_my_run(
    run_id: int,
    user=Depends(get_required_user),
    run_service: PlaybookRunService = Depends(_get_run_service),
):
    run = await run_service.get_user_run(user.id, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="运行记录不存在",
        )
    return detail_run(run)


@playbook.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_run(
    run_id: int,
    user=Depends(get_required_user),
    run_service: PlaybookRunService = Depends(_get_run_service),
):
    ok = await run_service.delete_user_run(user.id, run_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="运行记录不存在",
        )


# ---------------------------------------------------------------------------
# 工作流本身的端点 (参数化路径放最后)
# ---------------------------------------------------------------------------


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
