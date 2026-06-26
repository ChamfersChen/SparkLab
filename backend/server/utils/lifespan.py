"""应用启动/关闭钩子。

启动顺序：
1. 应用 Alembic 迁移至 head（开发期自动；生产期可改为手动）
2. 验证 Postgres 连接
3. 验证 Redis 连接
4. 创建初始超管（仅数据库无用户时）

关闭顺序：
1. 释放 DB 连接池
2. 释放 Redis 连接
"""

from contextlib import asynccontextmanager

from alembic.config import Config
from fastapi import FastAPI
from sparklab.config import get_settings
from sparklab.services.auth_service import AuthService
from sparklab.storage.postgres import dispose_engine, get_async_session, get_engine
from sparklab.storage.redis import close_redis, get_redis
from sparklab.utils.logger import logger

from alembic import command


def _run_migrations() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


async def _ensure_superadmin() -> None:
    settings = get_settings()
    async with get_async_session() as session:
        service = AuthService(session)
        await service.ensure_superadmin(
            settings.initial_superadmin_username,
            settings.initial_superadmin_password,
        )
    logger.info(
        "Initial superadmin checked",
        extra={"username": settings.initial_superadmin_username},
    )


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

    # 4. 创建初始超管
    await _ensure_superadmin()

    logger.info("SparkLab API startup complete")
    yield

    logger.info("SparkLab API shutting down...")
    await close_redis()
    await dispose_engine()
    logger.info("SparkLab API shutdown complete")
