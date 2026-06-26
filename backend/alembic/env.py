"""Alembic 异步迁移环境。

- target_metadata 取自 sparklab.models.Base.metadata
- 数据库 URL 取自 sparklab.config（不读 alembic.ini 中的 sqlalchemy.url）
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 让 alembic env.py 能 import 业务包
# （由 alembic.ini 中 prepend_sys_path 提供 . / package / server）

from sparklab.config import get_settings
from sparklab.models import Base  # noqa: F401  - 触发模型导入，让 autogenerate 能扫到

# 后续模型加入后，在 sparklab/models/__init__.py 中显式导出所有模型类即可

config = context.config

if config.config_file_name is not None:
    # 关键：disable_existing_loggers=False，否则 alembic 的 fileConfig 会把
    # 应用启动时已经配好的 sparklab / sparklab.access logger 全部禁用，
    # 导致 lifespan 之后所有业务日志和访问日志都不再输出。
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

_settings = get_settings()


def _get_url() -> str:
    return _settings.postgres_url


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 脚本但不执行。"""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """在线模式：通过异步引擎执行迁移。"""
    cfg_section = config.get_section(config.config_ini_section, {})
    cfg_section["sqlalchemy.url"] = _get_url()
    connectable = async_engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
