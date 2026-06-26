from fastapi import APIRouter, Depends, Header
from sparklab.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordChangeRequest,
    UserInfo,
)
from sparklab.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user

auth = APIRouter(prefix="/auth", tags=["认证"])


@auth.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.login(body.username, body.password)


@auth.post("/logout", response_model=MessageResponse)
async def logout(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        service = AuthService(db)
        await service.logout(token)
    return MessageResponse(message="已退出登录")


@auth.put("/password", response_model=MessageResponse)
async def change_password(
    body: PasswordChangeRequest,
    user=Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.change_password(user.id, body.old_password, body.new_password)
    return MessageResponse(message="密码修改成功")


@auth.get("/me", response_model=UserInfo)
async def get_me(user=Depends(get_required_user)):
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role.value,
        is_active=user.is_active,
    )
