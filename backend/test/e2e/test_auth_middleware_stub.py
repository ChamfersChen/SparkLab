"""auth_middleware 的契约测试。

阶段 1 中，4 个依赖函数都是骨架，调用 get_current_user 应抛 NotImplementedError。
此测试**锁定该契约**：当未来认证模块接入后，这些测试需要被替换为真实行为测试。
"""

import pytest

from server.utils.auth_middleware import (
    get_current_admin,
    get_current_super_admin,
    get_current_user,
    get_required_user,
)


@pytest.mark.asyncio
async def test_get_current_user_is_not_implemented() -> None:
    """阶段 1 占位：get_current_user 调用应抛 NotImplementedError。"""
    with pytest.raises(NotImplementedError):
        await get_current_user(authorization=None, db=None)


@pytest.mark.asyncio
async def test_get_required_user_propagates_not_implemented() -> None:
    """get_required_user 内部依赖 get_current_user，应一并抛 NotImplementedError。"""
    with pytest.raises(NotImplementedError):
        user = await get_current_user(authorization="Bearer fake", db=None)
        await get_required_user(user=user)


@pytest.mark.asyncio
async def test_get_current_admin_propagates_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        user = await get_current_user(authorization="Bearer fake", db=None)
        await get_current_admin(user=user)


@pytest.mark.asyncio
async def test_get_current_super_admin_propagates_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        user = await get_current_user(authorization="Bearer fake", db=None)
        await get_current_super_admin(user=user)
