"""认证依赖注入。

设计约定：
- JWT Token 通过 `Authorization: Bearer <token>` Header 传递
- 前端登录后把 Token 写入 localStorage；每次请求由请求拦截器注入 Header
- 路由通过 Depends(get_current_user) 拿到当前用户，None 表示未登录
- get_required_user / get_current_admin / get_current_super_admin
  会在权限不足时抛 401/403
"""

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sparklab.services.auth_service import AuthService
from sparklab.storage.postgres import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_async_session() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    service = AuthService(db)
    return await service.get_current_user_from_token(token)


async def get_required_user(user=Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请登录后再访问",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin(user=Depends(get_required_user)):
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


async def get_current_super_admin(user=Depends(get_required_user)):
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return user
