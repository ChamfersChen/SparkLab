"""tag_ids 串解析单元测试。

约定:
    "1,2;3,4"  → [[1,2],[3,4]]    组间 AND、组内 OR
    "1,2"      → [[1,2]]          单组退化为"或"
    "1"        → [[1]]            单值
    ""/None    → None             无筛选
    "abc;1,x"  → [[1]]            非数字字符静默跳过
"""

import pytest

from server.routers.template_router import _parse_tag_id_groups


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("1", [[1]]),
        ("1,2", [[1, 2]]),
        ("1,2;3", [[1, 2], [3]]),
        ("1,2;3,4", [[1, 2], [3, 4]]),
        # 空段/空成员/非数字静默丢弃,不抛 422
        ("1,;,2", [[1], [2]]),
        ("abc;1,x", [[1]]),
        (";;", None),
        # 顺序保留,组内重复保留(由 SQL EXISTS 隐式去重)
        ("3,1;2", [[3, 1], [2]]),
    ],
)
def test_parse_tag_id_groups(raw, expected):
    assert _parse_tag_id_groups(raw) == expected
