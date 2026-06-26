"""auth_middleware 的行为测试。

get_current_user 的完整功能验证依赖 httpx 集成测试（真实请求链路）；
单元层测试只验证依赖函数的直接行为。
"""

import pytest
from fastapi import HTTPException

from server.utils.auth_middleware import (
    get_current_admin,
    get_current_super_admin,
    get_current_user,
    get_required_user,
)


@pytest.mark.asyncio
async def test_get_current_user_no_auth_returns_none() -> None:
    user = await get_current_user(authorization=None, db=None)
    assert user is None


@pytest.mark.asyncio
async def test_get_current_user_invalid_prefix_returns_none() -> None:
    user = await get_current_user(authorization="Basic fake", db=None)
    assert user is None


@pytest.mark.asyncio
async def test_get_current_user_bearer_no_db_returns_none() -> None:
    user = await get_current_user(authorization="Bearer invalidtoken", db=None)
    assert user is None


@pytest.mark.asyncio
async def test_get_required_user_with_none_raises_401() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_required_user(user=None)
    assert exc.value.status_code == 401
