"""Postgres 连接的集成测试。

需要容器内的 postgres 服务可达。
"""

import pytest
import sqlalchemy
from sparklab.storage.postgres import get_async_session, get_engine


@pytest.mark.asyncio
async def test_engine_executes_select_one() -> None:
    """engine 能成功执行 SELECT 1。"""
    async with get_engine().begin() as conn:
        result = await conn.exec_driver_sql("SELECT 1")
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_async_session_context_yields_session() -> None:
    """get_async_session 上下文管理器能提供可用的会话。"""
    async with get_async_session() as session:
        result = await session.execute(sqlalchemy.text("SELECT 1"))
        assert result.scalar_one() == 1
