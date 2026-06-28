
"""管理员账号管理路由（超级管理员）。

- GET    /api/admin/admins                      → 分页查询管理员列表
- PUT    /api/admin/admins/{id}/role            → 更新角色
- PUT    /api/admin/admins/{id}/toggle          → 启用/禁用账号
- DELETE /api/admin/admins/{id}                 → 删除账号
- GET    /api/admin/admins/codes                → 查询管理员激活码列表
- POST   /api/admin/admins/codes/generate       → 生成管理员激活码
- PUT    /api/admin/admins/codes/{id}/toggle    → 启用/禁用激活码
- DELETE /api/admin/admins/codes/{id}           → 删除激活码
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sparklab.models.user import User
from sparklab.schemas.auth import (
    ActivationCodeListResponse,
    ActivationCodeWithUser,
    AdminUserInfo,
    AdminUserListResponse,
    GenerateCodesRequest,
    MessageResponse,
    UpdateRoleRequest,
)
from sparklab.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_current_super_admin, get_db

admin_account = APIRouter(
    prefix="/admins",
    tags=["admin-accounts"],
    dependencies=[Depends(get_current_super_admin)],
)


async def _get_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


# ========== 管理员账号管理 ==========


@admin_account.get("", response_model=AdminUserListResponse)
async def list_admin_users(
    role: str | None = Query(None, description="筛选：admin / super_admin"),
    active: bool | None = Query(None, description="筛选：是否启用"),
    search: str | None = Query(None, description="搜索用户名"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AuthService = Depends(_get_service),
):
    items, total = await service.list_admin_users(
        role_filter=role,
        active_filter=active,
        search=search,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AdminUserListResponse(
        items=[AdminUserInfo.model_validate(u) for u in items],
        total=total,
    )


@admin_account.put("/{user_id}/role", response_model=AdminUserInfo)
async def update_user_role(
    user_id: int,
    body: UpdateRoleRequest,
    current_user: User = Depends(get_current_super_admin),
    service: AuthService = Depends(_get_service),
):
    user = await service.update_user_role(user_id, body.role, current_user.id)
    return AdminUserInfo.model_validate(user)


@admin_account.put("/{user_id}/toggle", response_model=AdminUserInfo)
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_super_admin),
    service: AuthService = Depends(_get_service),
):
    user = await service.toggle_user_active(user_id, current_user.id)
    return AdminUserInfo.model_validate(user)


@admin_account.delete("/{user_id}", response_model=MessageResponse)
async def delete_admin_user(
    user_id: int,
    current_user: User = Depends(get_current_super_admin),
    service: AuthService = Depends(_get_service),
):
    deleted = await service.delete_user(user_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="删除失败",
        )
    return MessageResponse(message="账号已删除")


# ========== 管理员激活码管理 ==========


@admin_account.get("/codes", response_model=ActivationCodeListResponse)
async def list_admin_codes(
    status: str | None = Query(None, description="筛选：unused / used / disabled"),
    search: str | None = Query(None, description="搜索 code/note/username"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AuthService = Depends(_get_service),
):
    items, total = await service.list_admin_codes(
        status_filter=status,
        search=search,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return ActivationCodeListResponse(
        items=[ActivationCodeWithUser.model_validate(ac) for ac in items],
        total=total,
    )


@admin_account.post("/codes/generate", response_model=ActivationCodeListResponse)
async def generate_admin_codes(
    body: GenerateCodesRequest,
    current_user: User = Depends(get_current_super_admin),
    service: AuthService = Depends(_get_service),
):
    codes = await service.generate_admin_codes(
        count=body.count,
        note=body.note,
        creator_id=current_user.id,
    )
    return ActivationCodeListResponse(
        items=[ActivationCodeWithUser.model_validate(ac) for ac in codes],
        total=len(codes),
    )


@admin_account.put("/codes/{code_id}/toggle", response_model=MessageResponse)
async def toggle_admin_code(
    code_id: int,
    service: AuthService = Depends(_get_service),
):
    ac = await service.toggle_code_status(code_id)
    if ac is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="激活码不存在")
    new_status = "已启用" if ac.status == "unused" else "已禁用"
    return MessageResponse(message=f"激活码 {ac.code} {new_status}")


@admin_account.delete("/codes/{code_id}", response_model=MessageResponse)
async def delete_admin_code(
    code_id: int,
    service: AuthService = Depends(_get_service),
):
    deleted = await service.delete_code(code_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="激活码不存在或不可删除（仅未使用/已禁用的激活码可删除）",
        )
    return MessageResponse(message="激活码已删除")

