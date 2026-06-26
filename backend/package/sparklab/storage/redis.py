"""Redis 异步客户端单例 - 懒加载。

主要用途：
- JWT Token 黑名单（key: blacklist:<jti>，TTL = Token 剩余有效期）
- 后续可承载会话状态、缓存等

设计说明：
- 客户端在首次调用 `get_redis()` 时构造，避免 import 时立即读取环境变量。
"""

from redis.asyncio import Redis, from_url

from sparklab.config import get_settings

_client: Redis | None = None


def get_redis() -> Redis:
    """获取 Redis 客户端单例。"""
    global _client
    if _client is None:
        _client = from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """应用关闭时释放连接。"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
