"""sparklab.config.Settings 的单元测试。

通过 monkeypatch 设置环境变量，验证 Settings 能正确解析。
"""

import pytest
from pydantic import ValidationError


def _clear_settings_cache() -> None:
    """清空 get_settings 的 lru_cache，让每个测试拿到全新实例。"""
    from sparklab.config import get_settings

    get_settings.cache_clear()


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """设置 Settings 必填字段的默认值。"""
    monkeypatch.setenv("POSTGRES_URL", "postgresql+asyncpg://u:p@h:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://h:6379/0")
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("INITIAL_SUPERADMIN_PASSWORD", "init-pwd")


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """未显式设置的字段应取默认值。"""
    monkeypatch.delenv("SPARKLAB_ENV", raising=False)
    _set_required_env(monkeypatch)
    _clear_settings_cache()

    from sparklab.config import get_settings

    s = get_settings()
    assert s.sparklab_env == "development"
    assert s.jwt_algorithm == "HS256"
    assert s.jwt_expire_minutes == 43200
    assert s.initial_superadmin_username == "admin"
    assert s.tz == "Asia/Shanghai"


def test_settings_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """显式设置的环境变量应被读入。"""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SPARKLAB_ENV", "production")
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "120")
    monkeypatch.setenv("JWT_ALGORITHM", "HS512")
    _clear_settings_cache()

    from sparklab.config import get_settings

    s = get_settings()
    assert s.sparklab_env == "production"
    assert s.jwt_expire_minutes == 120
    assert s.jwt_algorithm == "HS512"


def test_settings_missing_required_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """缺少必填字段时应抛 ValidationError，让进程启动失败。"""
    for var in ("POSTGRES_URL", "REDIS_URL", "JWT_SECRET", "INITIAL_SUPERADMIN_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    # 阻止读 .env 文件，否则会被同目录下的 .env 覆盖
    monkeypatch.chdir(
        "/tmp" if not __import__("sys").platform.startswith("win") else __import__("tempfile").gettempdir()
    )
    _clear_settings_cache()

    from sparklab.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_invalid_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPARKLAB_ENV 不在 development/production 白名单时应抛 ValidationError。"""
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SPARKLAB_ENV", "staging")
    _clear_settings_cache()

    from sparklab.config import get_settings

    with pytest.raises(ValidationError):
        get_settings()
