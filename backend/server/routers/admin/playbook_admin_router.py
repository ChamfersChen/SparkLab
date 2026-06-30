"""工作流管理路由（管理员/超管）。

- GET    /api/admin/playbooks             → 工作流列表（全部状态，含搜索/标签/分页/排序）
- POST   /api/admin/playbooks             → 新建工作流
- GET    /api/admin/playbooks/{id}        → 工作流详情
- PUT    /api/admin/playbooks/{id}        → 编辑工作流
- PUT    /api/admin/playbooks/{id}/status → 切换状态
- DELETE /api/admin/playbooks/{id}        → 下线（软删 → archived）
- DELETE /api/admin/playbooks/{id}/hard   → 物理删除（仅超管）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.routers.template_router import _parse_tag_id_groups
from server.utils.auth_middleware import (
    get_current_admin,
    get_current_super_admin,
    get_db,
    get_required_user,
)
from sparklab.schemas.playbook import (
    PlaybookCreateRequest,
    PlaybookListResponse,
    PlaybookResponse,
    PlaybookStatusChangeRequest,
    PlaybookUpdateRequest,
)
from sparklab.services.playbook_service import PlaybookService


playbook_admin = APIRouter(
    prefix="/playbooks",
    tags=["admin-playbooks"],
    dependencies=[Depends(get_current_admin)],
)


async def _get_service(db: AsyncSession = Depends(get_db)) -> PlaybookService:
    return PlaybookService(db)


@playbook_admin.get("", response_model=PlaybookListResponse)
async def list_playbooks(
    search: str | None = Query(None, description="搜索标题/描述"),
    tag_ids: str | None = Query(
        None,
        description="标签筛选: 分号分组,逗号分隔成员。组间 AND、组内 OR,例如 '1,2;3'",
    ),
    status: str | None = Query(None, description="筛选：draft / published / archived"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("use_count", description="排序：use_count / newest"),
    service: PlaybookService = Depends(_get_service),
):
    items, total = await service.list_playbooks(
        search=search,
        tag_id_groups=_parse_tag_id_groups(tag_ids),
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return PlaybookListResponse(
        items=[PlaybookResponse.model_validate(p) for p in items],
        total=total,
    )


@playbook_admin.post("", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    body: PlaybookCreateRequest,
    current_user=Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    playbook_obj = await service.create_playbook(
        title=body.title,
        description=body.description,
        content=body.content,
        variable_hints=body.variable_hints,
        steps=body.steps,
        tag_ids=body.tag_ids,
        status=body.status,
        creator_id=current_user.id,
    )
    return PlaybookResponse.model_validate(playbook_obj)


@playbook_admin.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(
    playbook_id: int,
    service: PlaybookService = Depends(_get_service),
):
    obj = await service.get_playbook(playbook_id)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工作流不存在",
        )
    return PlaybookResponse.model_validate(obj)


@playbook_admin.put("/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: int,
    body: PlaybookUpdateRequest,
    service: PlaybookService = Depends(_get_service),
):
    kwargs = body.model_dump(exclude_none=True)
    return PlaybookResponse.model_validate(
        await service.update_playbook(playbook_id, **kwargs)
    )


@playbook_admin.put("/{playbook_id}/status", response_model=PlaybookResponse)
async def change_status(
    playbook_id: int,
    body: PlaybookStatusChangeRequest,
    service: PlaybookService = Depends(_get_service),
):
    return PlaybookResponse.model_validate(
        await service.change_status(playbook_id, body.status)
    )


@playbook_admin.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    playbook_id: int,
    service: PlaybookService = Depends(_get_service),
):
    await service.delete_playbook(playbook_id)


@playbook_admin.delete(
    "/{playbook_id}/hard",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_super_admin)],
)
async def hard_delete_playbook(
    playbook_id: int,
    service: PlaybookService = Depends(_get_service),
):
    await service.hard_delete_playbook(playbook_id)
