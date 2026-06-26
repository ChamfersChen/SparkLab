"""应用启动/关闭钩子。

启动顺序：
1. 应用 Alembic 迁移至 head（开发期自动；生产期可改为手动）
2. 验证 Postgres 连接
3. 验证 Redis 连接
4. （后续接入认证模块后）创建初始超管、预设默认 AI 平台、预设默认标签

关闭顺序：
1. 释放 DB 连接池
2. 释放 Redis 连接
"""

from contextlib import asynccontextmanager

from alembic.config import Config
from fastapi import FastAPI
from sparklab.storage.postgres import dispose_engine, get_engine
from sparklab.storage.redis import close_redis, get_redis
from sparklab.utils.logger import logger

from alembic import command


def _run_migrations() -> None:
    """同步调用 Alembic upgrade head。

    Alembic 的 command API 是同步的，在 lifespan 中通过 run_in_executor 即可。
    迁移失败应当抛出，让进程启动失败（不掩盖问题）。
    """
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio

    logger.info("SparkLab API starting...")

    # 1. Alembic 自动迁移
    try:
        await asyncio.get_event_loop().run_in_executor(None, _run_migrations)
        logger.info("Alembic migrations applied to head")
    except Exception:
        logger.exception("Alembic migration failed")
        raise

    # 2. 验证 Postgres 连接
    async with get_engine().begin() as conn:
        await conn.exec_driver_sql("SELECT 1")
    logger.info("Postgres connected")

    # 3. 验证 Redis 连接
    redis = get_redis()
    await redis.ping()
    logger.info("Redis connected")

    logger.info("SparkLab API startup complete")
    yield

    logger.info("SparkLab API shutting down...")
    await close_redis()
    await dispose_engine()
    logger.info("SparkLab API shutdown complete")
