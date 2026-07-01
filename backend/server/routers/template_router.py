"""模板路由（用户端）。

普通用户和管理员都可调用：
- GET    /api/templates              → 模板列表（搜索+标签+状态筛选+分页+排序）
- GET    /api/templates/runs         → 当前用户「模板使用记录」列表
- POST   /api/templates/runs         → 保存一次模板使用结果
- GET    /api/templates/runs/{run_id}→ 单条使用记录详情
- DELETE /api/templates/runs/{run_id}→ 删除一条使用记录
- GET    /api/templates/{id}         → 模板详情
- GET    /api/templates/{id}/fill    → 模板填写数据（变量提取 + hints）
- POST   /api/templates/{id}/use     → 使用计数 +1

可见性：published 模板对所有登录用户可见；draft/archived 仅作者本人可见（非作者 → 404）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.repositories.template_repository import detail_run
from sparklab.schemas.template import (
    FillDataResponse,
    TemplateListResponse,
    TemplateResponse,
    TemplateRunCreateRequest,
    TemplateRunDetail,
    TemplateRunListResponse,
)
from sparklab.services.template_service import TemplateService, TemplateRunService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user

template = APIRouter(prefix="/templates", tags=["模板"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


async def _get_run_service(db: AsyncSession = Depends(get_db)) -> TemplateRunService:
    return TemplateRunService(db)


def _parse_tag_id_groups(raw: str | None) -> list[list[int]] | None:
    """解析 tag_ids 串。

    形式: "1,2;3,4" → [[1,2],[3,4]] (组间 AND,组内 OR)。
    单组退化: "1,2" → [[1,2]] (语义等价于"或");
    单值退化: "1" → [[1]];
    空/None → None。
    非法/非数字字符静默跳过,避免 422 干扰用户。
    """
    if not raw:
        return None
    groups: list[list[int]] = []
    for chunk in raw.split(";"):
        ids = [int(t) for t in chunk.split(",") if t.strip().isdigit()]
        if ids:
            groups.append(ids)
    return groups or None


# ---------------------------------------------------------------------------
# 使用记录 (个人中心 / 我的模板使用记录)
# 必须在 {template_id} 路径之前声明, 否则会被参数化路径吞掉
# ---------------------------------------------------------------------------

@template.get("/runs", response_model=TemplateRunListResponse)
async def list_my_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_required_user),
    run_service: TemplateRunService = Depends(_get_run_service),
):
    """当前用户的模板使用记录列表, 按 created_at DESC."""
    items, total = await run_service.list_user_runs(
        user.id, offset=(page - 1) * page_size, limit=page_size,
    )
    return TemplateRunListResponse(items=items, total=total)


@template.post("/runs", response_model=TemplateRunDetail, status_code=status.HTTP_201_CREATED)
async def create_run(
    body: TemplateRunCreateRequest,
    user=Depends(get_required_user),
    run_service: TemplateRunService = Depends(_get_run_service),
):
    """保存一次模板使用结果."""
    run = await run_service.create_run(
        user=user,
        template_id=body.template_id,
        title=body.title,
        generated_prompt=body.generated_prompt,
        form_values=body.form_values,
        ai_result=body.ai_result,
    )
    return detail_run(run)


@template.get("/runs/{run_id}", response_model=TemplateRunDetail)
async def get_my_run(
    run_id: int,
    user=Depends(get_required_user),
    run_service: TemplateRunService = Depends(_get_run_service),
):
    run = await run_service.get_user_run(user.id, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用记录不存在",
        )
    return detail_run(run)


@template.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_run(
    run_id: int,
    user=Depends(get_required_user),
    run_service: TemplateRunService = Depends(_get_run_service),
):
    ok = await run_service.delete_user_run(user.id, run_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用记录不存在",
        )


# ---------------------------------------------------------------------------
# 模板本身的端点 (参数化路径放最后)
# ---------------------------------------------------------------------------

@template.get("", response_model=TemplateListResponse)
async def list_templates(
    search: str | None = Query(None, description="搜索标题/描述"),
    tag_ids: str | None = Query(
        None,
        description="标签筛选: 分号分组,逗号分隔成员。组间 AND、组内 OR,例如 '1,2;3'",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("use_count", description="排序：use_count / newest"),
    user=Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """已发布的模板列表（用户端）。"""
    items, total = await service.list_templates(
        search=search,
        tag_id_groups=_parse_tag_id_groups(tag_ids),
        status="published",
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in items],
        total=total,
    )


@template.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    current_user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    template = await service.get_template_for_user(template_id, current_user.id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return TemplateResponse.model_validate(template)


@template.get("/{template_id}/fill", response_model=FillDataResponse)
async def get_fill_data(
    template_id: int,
    current_user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """获取模板填写页所需数据（content + 变量提示）。"""
    template = await service.get_template_for_user(template_id, current_user.id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return FillDataResponse(
        template_id=template.id,
        title=template.title,
        description=template.description,
        content=template.content or "",
        variable_hints=template.variable_hints or {},
    )


@template.post("/{template_id}/use", response_model=dict)
async def increment_use(
    template_id: int,
    current_user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    template = await service.get_template_for_user(template_id, current_user.id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    await service.increment_use_count(template_id)
    return {"message": "ok"}
