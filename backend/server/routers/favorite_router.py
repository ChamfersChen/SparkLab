"""收藏路由（用户端）。

- GET    /api/favorites              → 获取当前用户收藏列表
- POST   /api/favorites              → 切换收藏状态 (toggle)
- DELETE /api/favorites/{type}/{id}  → 取消收藏
- GET    /api/favorites/check        → 查询是否已收藏
"""

from fastapi import APIRouter, Depends, Query
from sparklab.models.favorite import FavoriteTargetType
from sparklab.schemas.favorite import (
    FavoriteCreateRequest,
    FavoriteListResponse,
    FavoriteResponse,
)
from sparklab.services.favorite_service import FavoriteService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user

favorite = APIRouter(prefix="/favorites", tags=["收藏"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> FavoriteService:
    return FavoriteService(db)


@favorite.get("", response_model=FavoriteListResponse)
async def list_favorites(
    type: str | None = Query(None, description="筛选类型: template 或 playbook"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user=Depends(get_required_user),
    service: FavoriteService = Depends(_get_service),
):
    target_type = FavoriteTargetType(type) if type else None
    items, total = await service.list_favorites(
        user.id, target_type=target_type, page=page, page_size=page_size
    )
    return FavoriteListResponse(
        items=[FavoriteResponse(**item) for item in items],
        total=total,
    )


@favorite.post("")
async def toggle_favorite(
    body: FavoriteCreateRequest,
    user=Depends(get_required_user),
    service: FavoriteService = Depends(_get_service),
):
    target_type = FavoriteTargetType(body.target_type)
    result = await service.toggle(user.id, target_type, body.target_id)
    return result


@favorite.delete("/{target_type}/{target_id}")
async def remove_favorite(
    target_type: str,
    target_id: int,
    user=Depends(get_required_user),
    service: FavoriteService = Depends(_get_service),
):
    t = FavoriteTargetType(target_type)
    from sparklab.repositories.favorite_repository import FavoriteRepository
    repo = FavoriteRepository(service.db)
    deleted = await repo.delete(user.id, t, target_id)
    await service.db.commit()
    return {"favorited": False, "deleted": deleted}


@favorite.get("/check")
async def check_favorited(
    type: str = Query(..., description="目标类型: template 或 playbook"),
    id: int = Query(..., gt=0, description="目标 ID"),
    user=Depends(get_required_user),
    service: FavoriteService = Depends(_get_service),
):
    target_type = FavoriteTargetType(type)
    favorited = await service.check_favorited(user.id, target_type, id)
    return {"favorited": favorited}
