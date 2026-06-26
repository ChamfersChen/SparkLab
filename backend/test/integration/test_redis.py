"""Redis 连接的集成测试。

需要容器内的 redis 服务可达。
"""

import pytest
from sparklab.storage.redis import close_redis, get_redis


@pytest.mark.asyncio
async def test_redis_ping() -> None:
    """Redis 客户端能成功 PING。"""
    redis = get_redis()
    pong = await redis.ping()
    assert pong is True


@pytest.mark.asyncio
async def test_redis_set_and_get() -> None:
    """Redis 客户端能 SET / GET。"""
    redis = get_redis()
    await redis.set("sparklab:test:hello", "world", ex=60)
    value = await redis.get("sparklab:test:hello")
    assert value == "world"
    await redis.delete("sparklab:test:hello")


@pytest.mark.asyncio
async def test_get_redis_returns_singleton() -> None:
    """多次调用 get_redis 返回同一个实例。"""
    a = get_redis()
    b = get_redis()
    assert a is b


@pytest.mark.asyncio
async def test_close_redis_then_get_creates_new_client() -> None:
    """close_redis 后再 get_redis 应得到新实例。"""
    a = get_redis()
    await close_redis()
    b = get_redis()
    assert a is not b
    # 清理：保证后续测试能继续用
    await close_redis()
