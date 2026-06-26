"""激活码管理路由（超级管理员）。

- GET    /api/admin/activation-codes                → 分页查询列表
- POST   /api/admin/activation-codes/generate       → 批量生成
- PUT    /api/admin/activation-codes/{id}/toggle     → 启用/禁用
- PUT    /api/admin/activation-codes/{id}/note       → 编辑备注
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.schemas.auth import (
    ActivationCodeListResponse,
    ActivationCodeWithUser,
    GenerateCodesRequest,
    MessageResponse,
    UpdateNoteRequest,
)
from sparklab.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_current_super_admin, get_db

activation_code_admin = APIRouter(
    prefix="/activation-codes",
    tags=["admin-activation-codes"],
    dependencies=[Depends(get_current_super_admin)],
)


async def _get_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@activation_code_admin.get("", response_model=ActivationCodeListResponse)
async def list_activation_codes(
    status: str | None = Query(None, description="筛选：unused / used / disabled"),
    search: str | None = Query(None, description="搜索 code/note/username"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AuthService = Depends(_get_service),
):
    items, total = await service.list_codes(
        status_filter=status,
        search=search,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ActivationCodeListResponse(
        items=[ActivationCodeWithUser.model_validate(ac) for ac in items],
        total=total,
    )


@activation_code_admin.post("/generate", response_model=ActivationCodeListResponse)
async def generate_activation_codes(
    body: GenerateCodesRequest,
    current_user: User = Depends(get_current_super_admin),
    service: AuthService = Depends(_get_service),
):
    codes = await service.generate_codes(count=body.count, note=body.note, creator_id=current_user.id)
    return ActivationCodeListResponse(
        items=[ActivationCodeWithUser.model_validate(ac) for ac in codes],
        total=len(codes),
    )


@activation_code_admin.put("/{code_id}/toggle", response_model=MessageResponse)
async def toggle_activation_code(
    code_id: int,
    service: AuthService = Depends(_get_service),
):
    ac = await service.toggle_code_status(code_id)
    if ac is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="激活码不存在")
    new_status = "已启用" if ac.status == "unused" else "已禁用"
    return MessageResponse(message=f"激活码 {ac.code} {new_status}")


@activation_code_admin.put("/{code_id}/note", response_model=ActivationCodeWithUser)
async def update_code_note(
    code_id: int,
    body: UpdateNoteRequest,
    service: AuthService = Depends(_get_service),
):
    ac = await service.update_code_note(code_id, body.note)
    if ac is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="激活码不存在")
    return ActivationCodeWithUser.model_validate(ac)
