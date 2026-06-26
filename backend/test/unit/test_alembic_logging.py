"""Alembic env.py 配置的契约测试。

锁定：alembic/env.py 在调用 logging.config.fileConfig 时必须传
disable_existing_loggers=False，否则会把应用启动时已经配置的
sparklab / sparklab.access logger 静默禁用，导致请求日志不输出。
"""

from pathlib import Path


def test_alembic_env_disables_existing_loggers_false() -> None:
    """alembic/env.py 中 fileConfig 调用必须显式 disable_existing_loggers=False。"""
    env_py = Path(__file__).resolve().parents[2] / "alembic" / "env.py"
    src = env_py.read_text(encoding="utf-8")

    # 必须出现 fileConfig 调用
    assert "fileConfig(" in src, "alembic/env.py 应仍在调用 fileConfig"

    # 该调用必须显式关闭"禁用已有 logger"行为
    assert "disable_existing_loggers=False" in src, (
        "alembic/env.py 的 fileConfig 必须传 disable_existing_loggers=False，"
        "否则会禁用应用已经配置的 sparklab 业务/访问 logger。"
    )
