"""模板管理路由（管理员/超管）。

- GET    /api/admin/templates             → 模板列表（全部状态，含搜索/标签/分页）
- POST   /api/admin/templates             → 新建模板
- GET    /api/admin/templates/{id}        → 模板详情
- PUT    /api/admin/templates/{id}        → 编辑模板
- DELETE /api/admin/templates/{id}        → 下线模板（软删除 → archived）
- PUT    /api/admin/templates/{id}/status → 切换状态
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.schemas.template import (
    TemplateCreateRequest,
    TemplateListResponse,
    TemplateResponse,
    TemplateStatusChangeRequest,
    TemplateUpdateRequest,
)
from sparklab.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession

from server.routers.template_router import _parse_tag_id_groups
from server.utils.auth_middleware import get_current_admin, get_current_super_admin, get_db, get_required_user

template_admin = APIRouter(
    prefix="/templates",
    tags=["admin-templates"],
    dependencies=[Depends(get_current_admin)],
)


async def _get_service(db: AsyncSession = Depends(get_db)) -> TemplateService:
    return TemplateService(db)


@template_admin.get("", response_model=TemplateListResponse)
async def list_templates(
    search: str | None = Query(None, description="搜索标题/描述"),
    tag_ids: str | None = Query(
        None,
        description="标签筛选: 分号分组,逗号分隔成员。组间 AND、组内 OR,例如 '1,2;3'",
    ),
    status: str | None = Query(None, description="筛选：draft / published / archived"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", description="排序：use_count / newest"),
    service: TemplateService = Depends(_get_service),
):
    """管理员模板列表（仅公开模板，不包含普通用户私有模板）。"""
    items, total = await service.list_templates(
        search=search,
        tag_id_groups=_parse_tag_id_groups(tag_ids),
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        include_private=False,  # 管理员不查看普通用户的私有模板
    )
    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in items],
        total=total,
    )


@template_admin.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreateRequest,
    current_user: User = Depends(get_required_user),
    service: TemplateService = Depends(_get_service),
):
    template = await service.create_template(
        title=body.title,
        description=body.description,
        content=body.content,
        variable_hints=body.variable_hints,
        tag_ids=body.tag_ids,
        status=body.status,
        creator_id=current_user.id,
    )
    return TemplateResponse.model_validate(template)


@template_admin.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    service: TemplateService = Depends(_get_service),
):
    template = await service.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return TemplateResponse.model_validate(template)


@template_admin.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    body: TemplateUpdateRequest,
    service: TemplateService = Depends(_get_service),
):
    kwargs = body.model_dump(exclude_none=True)
    template = await service.update_template(template_id, **kwargs)
    return TemplateResponse.model_validate(template)


@template_admin.put("/{template_id}/status", response_model=TemplateResponse)
async def change_template_status(
    template_id: int,
    body: TemplateStatusChangeRequest,
    service: TemplateService = Depends(_get_service),
):
    template = await service.change_status(template_id, body.status)
    return TemplateResponse.model_validate(template)


@template_admin.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    service: TemplateService = Depends(_get_service),
):
    await service.delete_template(template_id)


@template_admin.delete(
    "/{template_id}/hard",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_super_admin)],
)
async def hard_delete_template(
    template_id: int,
    service: TemplateService = Depends(_get_service),
):
    """物理删除模板（仅超管）：从 DB 删除该条记录，template_tags 关联 CASCADE 自动清理。

    与软删（archived）不同：此操作不可恢复，请谨慎使用。
    """
    await service.hard_delete_template(template_id)
