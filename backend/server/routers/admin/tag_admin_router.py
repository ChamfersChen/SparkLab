"""标签管理路由（管理员/超管）。

- GET    /api/admin/tags          → 标签列表（支持 category 筛选）
- POST   /api/admin/tags          → 新增标签
- PUT    /api/admin/tags/{id}     → 更新标签（名称/排序）
- DELETE /api/admin/tags/{id}     → 删除标签
"""

from fastapi import APIRouter, Depends, Query, status
from sparklab.schemas.tag import TagCreateRequest, TagListResponse, TagResponse, TagUpdateRequest
from sparklab.services.tag_service import TagService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_current_admin, get_db

tag_admin = APIRouter(
    prefix="/tags",
    tags=["admin-tags"],
    dependencies=[Depends(get_current_admin)],
)


async def _get_service(db: AsyncSession = Depends(get_db)) -> TagService:
    return TagService(db)


@tag_admin.get("", response_model=TagListResponse)
async def list_tags(
    category: str | None = Query(None, description="筛选：platform / content_type / industry"),
    service: TagService = Depends(_get_service),
):
    items, total = await service.list_tags(category)
    return TagListResponse(
        items=[TagResponse.model_validate(t) for t in items],
        total=total,
    )


@tag_admin.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    body: TagCreateRequest,
    service: TagService = Depends(_get_service),
):
    tag = await service.create_tag(body.name, body.category, body.sort_order)
    return TagResponse.model_validate(tag)


@tag_admin.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    body: TagUpdateRequest,
    service: TagService = Depends(_get_service),
):
    tag = await service.update_tag(tag_id, body.name, body.sort_order)
    return TagResponse.model_validate(tag)


@tag_admin.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    service: TagService = Depends(_get_service),
):
    await service.delete_tag(tag_id)
