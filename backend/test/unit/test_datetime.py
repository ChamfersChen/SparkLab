"""sparklab.utils.datetime 的单元测试。"""

from datetime import UTC, datetime, timedelta

from sparklab.utils.datetime import utc_now, utc_now_naive


def test_utc_now_returns_aware_datetime() -> None:
    """utc_now 返回带时区信息的 datetime。"""
    now = utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_utc_now_naive_returns_naive_datetime() -> None:
    """utc_now_naive 返回不带时区信息的 datetime。"""
    now = utc_now_naive()
    assert isinstance(now, datetime)
    assert now.tzinfo is None


def test_utc_now_and_naive_match() -> None:
    """同一时刻调用，两者的年月日时分秒应一致（允许 1 秒误差）。"""
    aware = utc_now()
    naive = utc_now_naive()
    delta = abs((aware.replace(tzinfo=None) - naive).total_seconds())
    assert delta < 1.0


def test_utc_now_is_close_to_system_utc() -> None:
    """utc_now 与系统 UTC 时间应接近。"""
    expected = datetime.now(UTC)
    actual = utc_now()
    delta = abs((expected - actual).total_seconds())
    assert delta < 1.0
