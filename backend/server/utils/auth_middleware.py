"""认证依赖注入骨架。

⚠️ 阶段 1 仅定义函数签名，所有真实逻辑等认证模块（激活码、JWT、密码）
接入后再实现。当前调用任意一个会抛 NotImplementedError，明确告诉调用方
"这条路径还没接通"，避免用半成品的 stub 静默放行请求。

设计约定：
- JWT Token 通过 `Authorization: Bearer <token>` Header 传递
- 前端登录后把 Token 写入 localStorage；每次请求由请求拦截器注入 Header
- 路由通过 Depends(get_current_user) 拿到当前用户，None 表示未登录
- get_required_user / get_current_admin / get_current_super_admin
  会在权限不足时抛 401/403
"""

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sparklab.storage.postgres import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncIterator[AsyncSession]:
    """注入异步数据库会话。"""
    async with get_async_session() as session:
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """从 Authorization Header 中解析 JWT，加载用户对象；未登录返回 None。

    待实现：
    1. 若 authorization 为空或不是 "Bearer xxx" 格式 → 返回 None
    2. 校验 JWT 签名、有效期、jti 不在 Redis 黑名单
    3. 查询 User 表，验证 is_active
    4. 返回 User 实例
    """
    raise NotImplementedError("认证模块尚未接入，禁止使用该依赖")


async def get_required_user(user=Depends(get_current_user)):
    """已登录用户依赖；未登录抛 401。"""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请登录后再访问",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_admin(user=Depends(get_required_user)):
    """管理员或超管依赖；权限不足抛 403。"""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user


async def get_current_super_admin(user=Depends(get_required_user)):
    """超级管理员依赖；权限不足抛 403。"""
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return user
