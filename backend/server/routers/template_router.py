"""模板路由（用户端）。

普通用户和管理员都可调用：
- GET    /api/templates              → 模板列表（搜索+标签+状态筛选+分页+排序）
- GET    /api/templates/{id}         → 模板详情
- GET    /api/templates/{id}/fill    → 模板填写数据（变量提取 + hints）
- POST   /api/templates/{id}/use     → 使用计数 +1

可见性：published 模板对所有登录用户可见；draft/archived 仅作者本人可见（非作者 → 404）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.schemas.template import (
    FillDataResponse,
    TemplateListResponse,
    TemplateResponse,
)
from sparklab.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user

template = APIRouter(prefix="/templates", tags=["模板"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


@template.get("", response_model=TemplateListResponse)
async def list_templates(
    search: str | None = Query(None, description="搜索标题/描述"),
    tag_ids: str | None = Query(None, description="逗号分隔的标签 ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("use_count", description="排序：use_count / newest"),
    user=Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """已发布的模板列表（用户端）。"""
    parsed_tag_ids = [int(t) for t in tag_ids.split(",") if t.strip().isdigit()] if tag_ids else None
    items, total = await service.list_templates(
        search=search,
        tag_ids=parsed_tag_ids,
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
    """获取模板填写页所需数据（变量清单 + hints）。"""
    template = await service.get_template_for_user(template_id, current_user.id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return FillDataResponse(
        template_id=template.id,
        title=template.title,
        description=template.description,
        role=template.role,
        goal=template.goal,
        input=template.input,
        output=template.output,
        example=template.example,
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
