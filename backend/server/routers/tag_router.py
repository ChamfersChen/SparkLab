"""标签路由（用户端）。

普通用户和管理员都可调用 GET /api/tags 获取标签列表（按分类分组）。
"""

from fastapi import APIRouter, Depends
from sparklab.schemas.tag import TagResponse
from sparklab.services.tag_service import TagService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user

tag = APIRouter(prefix="/tags", tags=["标签"])


async def _get_service(db: AsyncSession = Depends(get_db)) -> TagService:
    return TagService(db)


@tag.get("", response_model=dict)
async def list_tags_grouped(
    user=Depends(get_required_user),
    service: TagService = Depends(_get_service),
):
    grouped = await service.list_by_category_grouped()
    return {cat: [TagResponse.model_validate(t) for t in items] for cat, items in grouped.items()}
