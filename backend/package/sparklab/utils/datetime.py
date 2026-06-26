"""时间工具 - 统一以 UTC naive datetime 入库。"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """当前 UTC 时间（带时区信息）。"""
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """当前 UTC 时间（不带时区信息），适合直接入库到 TIMESTAMP WITHOUT TIME ZONE 列。"""
    return datetime.now(UTC).replace(tzinfo=None)
