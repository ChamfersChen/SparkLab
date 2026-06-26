"""SparkLab 全局配置 - 通过 pydantic-settings 从环境变量加载。

使用方式：
    from sparklab.config import get_settings
    settings = get_settings()

`get_settings` 用 lru_cache 缓存，整个进程只构造一次 Settings 实例。
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- 运行环境 ---
    sparklab_env: Literal["development", "production"] = "development"
    sparklab_cors_origins: str = ""

    # --- 数据库 ---
    postgres_url: str

    # --- Redis ---
    redis_url: str

    # --- JWT ---
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 43200  # 默认 30 天

    # --- 初始超管 ---
    initial_superadmin_username: str = "admin"
    initial_superadmin_password: str

    # --- 时区 ---
    tz: str = "Asia/Shanghai"


@lru_cache
def get_settings() -> Settings:
    return Settings()
