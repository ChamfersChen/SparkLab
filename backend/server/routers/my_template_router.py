"""我的模板路由（普通用户）。

普通用户可以管理自己创建的模板：
- GET    /api/my/templates              → 我的模板列表
- POST   /api/my/templates              → 新建模板（自动设为私有）
- GET    /api/my/templates/{id}         → 模板详情（仅自己的）
- PUT    /api/my/templates/{id}         → 编辑模板（仅自己的）
- DELETE /api/my/templates/{id}         → 删除模板（仅自己的）

注意：用户创建的模板自动设为私有（is_private=True），对其他用户不可见。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.schemas.template import (
    TemplateCreateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdateRequest,
)
from sparklab.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from server.routers.template_router import _parse_tag_id_groups

my_templates = APIRouter(prefix="/my/templates", tags=["我的模板"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


@my_templates.get("", response_model=TemplateListResponse)
async def list_my_templates(
    search: str | None = Query(None, description="搜索标题/描述"),
    status: str | None = Query(None, description="筛选：draft / published / archived"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", description="排序：use_count / newest"),
    user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """当前用户的模板列表（包含私有和公开的）。"""
    items, total = await service.list_user_templates(
        user_id=user.id,
        search=search,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in items],
        total=total,
    )


@my_templates.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_my_template(
    body: TemplateCreateRequest,
    user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """创建模板（自动设为私有）。"""
    template = await service.create_template(
        title=body.title,
        description=body.description,
        content=body.content,
        variable_hints=body.variable_hints,
        tag_ids=body.tag_ids,
        status=body.status,
        creator_id=user.id,
        is_private=True,  # 用户创建的模板自动设为私有
    )
    return TemplateResponse.model_validate(template)


@my_templates.get("/{template_id}", response_model=TemplateResponse)
async def get_my_template(
    template_id: int,
    user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """获取模板详情（仅自己的模板）。"""
    template = await service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    # 校验是否为自己的模板
    if template.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return TemplateResponse.model_validate(template)


@my_templates.put("/{template_id}", response_model=TemplateResponse)
async def update_my_template(
    template_id: int,
    body: TemplateUpdateRequest,
    user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """编辑模板（仅自己的模板）。"""
    # 先校验是否为自己的模板
    template = await service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    if template.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")

    kwargs = body.model_dump(exclude_none=True)
    template = await service.update_template(template_id, **kwargs)
    return TemplateResponse.model_validate(template)


@my_templates.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_template(
    template_id: int,
    user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    """删除模板（仅自己的模板，软删除）。"""
    # 先校验是否为自己的模板
    template = await service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    if template.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")

    await service.delete_template(template_id)
