"""我的流程路由（普通用户）。

普通用户可以管理自己创建的流程：
- GET    /api/my/playbooks              → 我的流程列表
- POST   /api/my/playbooks              → 新建流程（自动设为私有）
- GET    /api/my/playbooks/{id}         → 流程详情（仅自己的）
- PUT    /api/my/playbooks/{id}         → 编辑流程（仅自己的）
- DELETE /api/my/playbooks/{id}         → 删除流程（仅自己的）

注意：用户创建的流程自动设为私有（is_private=True），对其他用户不可见。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.schemas.playbook import (
    PlaybookCreateRequest,
    PlaybookListResponse,
    PlaybookResponse,
    PlaybookUpdateRequest,
)
from sparklab.services.playbook_service import PlaybookService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user

my_playbooks = APIRouter(prefix="/my/playbooks", tags=["我的流程"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> PlaybookService:
    return PlaybookService(db)


@my_playbooks.get("", response_model=PlaybookListResponse)
async def list_my_playbooks(
    search: str | None = Query(None, description="搜索标题/描述"),
    status: str | None = Query(None, description="筛选：draft / published / archived"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("newest", description="排序：use_count / newest"),
    user: User = Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    """当前用户的流程列表（包含私有和公开的）。"""
    items, total = await service.list_user_playbooks(
        user_id=user.id,
        search=search,
        status=status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
    )
    return PlaybookListResponse(
        items=[PlaybookResponse.model_validate(p) for p in items],
        total=total,
    )


@my_playbooks.post("", response_model=PlaybookResponse, status_code=status.HTTP_201_CREATED)
async def create_my_playbook(
    body: PlaybookCreateRequest,
    user: User = Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    """创建流程（自动设为私有）。"""
    playbook = await service.create_playbook(
        title=body.title,
        description=body.description,
        content=body.content,
        variable_hints=body.variable_hints,
        steps=body.steps,
        tag_ids=body.tag_ids,
        status=body.status,
        creator_id=user.id,
        is_private=True,  # 用户创建的流程自动设为私有
    )
    return PlaybookResponse.model_validate(playbook)


@my_playbooks.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_my_playbook(
    playbook_id: int,
    user: User = Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    """获取流程详情（仅自己的流程）。"""
    playbook = await service.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程不存在")
    # 校验是否为自己的流程
    if playbook.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程不存在")
    return PlaybookResponse.model_validate(playbook)


@my_playbooks.put("/{playbook_id}", response_model=PlaybookResponse)
async def update_my_playbook(
    playbook_id: int,
    body: PlaybookUpdateRequest,
    user: User = Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    """编辑流程（仅自己的流程）。"""
    # 先校验是否为自己的流程
    playbook = await service.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程不存在")
    if playbook.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程不存在")

    kwargs = body.model_dump(exclude_none=True)
    playbook = await service.update_playbook(playbook_id, **kwargs)
    return PlaybookResponse.model_validate(playbook)


@my_playbooks.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_playbook(
    playbook_id: int,
    user: User = Depends(get_required_user),
    service: PlaybookService = Depends(_get_service),
):
    """删除流程（仅自己的流程，软删除）。"""
    # 先校验是否为自己的流程
    playbook = await service.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程不存在")
    if playbook.creator_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="流程不存在")

    await service.delete_playbook(playbook_id)
