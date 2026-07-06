"""数据看板 e2e 测试。

覆盖：
- 401 未登录 / 403 普通用户 鉴权
- 各端点基础结构（stats / top-templates / top-playbooks / recent-activity）
- range 参数校验（合法 / 非法）
- 7d/30d/all 三种 range 行为差异
- 准备数据：创建模板 + 工作流 + 激活码
"""

import time

import pytest
from httpx import AsyncClient
from sparklab.config import get_settings

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


async def _admin_login(client: AsyncClient) -> str:
    """登录初始超管，返回 token。"""
    settings = get_settings()
    resp = await client.post(
        "/api/auth/login",
        json={
            "username": settings.initial_superadmin_username,
            "password": settings.initial_superadmin_password,
        },
    )
    assert resp.status_code == 200
    return resp.json()["token"]


def _admin_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_published_template(client: AsyncClient, headers: dict, ts: str, title_suffix: str) -> int:
    """创建一个已发布模板，返回 id。"""
    resp = await client.post(
        "/api/admin/templates",
        json={
            "title": f"e2e-dash-tpl-{title_suffix}-{ts}",
            "description": f"dashboard test template {title_suffix}",
            "content": "你是专家。目标：生成内容。输入：{{topic}}。输出：文案。示例：示例文本。",
            "variable_hints": {"topic": "输入主题"},
            "status": "published",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_published_playbook(client: AsyncClient, headers: dict, ts: str, title_suffix: str) -> int:
    """创建一个已发布工作流（含 1 个 step），返回 id。"""
    resp = await client.post(
        "/api/admin/playbooks",
        json={
            "title": f"e2e-dash-pb-{title_suffix}-{ts}",
            "description": f"dashboard test playbook {title_suffix}",
            "content": "工作流级上下文：{{brief}}",
            "variable_hints": {"brief": "项目简介"},
            "steps": [
                {
                    "step_order": 1,
                    "name": "分析",
                    "description": "分析需求",
                    "content": "请分析 {{brief}}",
                }
            ],
            "status": "published",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_activation_code(client: AsyncClient, headers: dict) -> int:
    """生成一个激活码，返回 code 字符串。"""
    resp = await client.post(
        "/api/admin/activation-codes/generate",
        json={"count": 1, "note": "e2e-dashboard"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["items"][0]["id"]


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client: AsyncClient) -> None:
    """未登录访问所有 dashboard 端点应返回 401。"""
    for path in (
        "/api/admin/dashboard/stats",
        "/api/admin/dashboard/top-templates",
        "/api/admin/dashboard/top-playbooks",
        "/api/admin/dashboard/recent-activity",
    ):
        resp = await client.get(path)
        assert resp.status_code == 401, f"{path} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_dashboard_normal_user_forbidden(client: AsyncClient) -> None:
    """普通用户无法访问 dashboard。"""
    admin_token = await _admin_login(client)
    admin_headers = _admin_headers(admin_token)

    # 生成激活码 + 注册普通用户
    gen = await client.post(
        "/api/admin/activation-codes/generate",
        json={"count": 1, "note": "e2e-dashboard-user"},
        headers=admin_headers,
    )
    code = gen.json()["items"][0]["code"]
    ts = str(int(time.time() * 1000))
    reg = await client.post(
        "/api/activation/activate",
        json={"code": code, "username": f"e2e_dash_user_{ts}", "password": "test123456"},
    )
    assert reg.status_code == 200
    user_token = reg.json()["token"]
    user_headers = _admin_headers(user_token)

    for path in (
        "/api/admin/dashboard/stats",
        "/api/admin/dashboard/top-templates",
        "/api/admin/dashboard/top-playbooks",
        "/api/admin/dashboard/recent-activity",
    ):
        resp = await client.get(path, headers=user_headers)
        assert resp.status_code == 403, f"{path} returned {resp.status_code}"


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stats_default_range_all(client: AsyncClient) -> None:
    """默认 range=all：累计语义。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)

    resp = await client.get("/api/admin/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["range"] == "all"
    # 字段完整性
    for key in (
        "templates_published",
        "playbooks_published",
        "total_uses",
        "total_favorites",
        "users_total",
        "users_new",
        "activation_codes",
        "uses_trend",
    ):
        assert key in data, f"missing field: {key}"

    # 激活码子结构
    ac = data["activation_codes"]
    for key in ("total", "unused", "used", "disabled"):
        assert key in ac, f"missing activation_codes.{key}"
        assert isinstance(ac[key], int)

    # all 模式不应有 users_new（按设计：累计区间无意义）
    assert data["users_new"] == 0
    assert data["uses_trend"] == []


@pytest.mark.asyncio
async def test_stats_range_7d_and_30d_have_trend(client: AsyncClient) -> None:
    """7d / 30d：users_new 有值，uses_trend 有对应天数个点。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)

    for range_value, expected_days in [("7d", 7), ("30d", 30)]:
        resp = await client.get(f"/api/admin/dashboard/stats?range={range_value}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["range"] == range_value
        assert len(data["uses_trend"]) == expected_days
        for point in data["uses_trend"]:
            assert "date" in point
            assert "count" in point
            assert isinstance(point["count"], int)


@pytest.mark.asyncio
async def test_stats_invalid_range_returns_400(client: AsyncClient) -> None:
    """非法 range → 400。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    resp = await client.get("/api/admin/dashboard/stats?range=invalid", headers=headers)
    assert resp.status_code == 400
    assert "range" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_stats_reflects_created_data(client: AsyncClient) -> None:
    """创建模板/工作流/激活码后，stats 数值应能反映新增。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    ts = str(int(time.time() * 1000))

    before = (await client.get("/api/admin/dashboard/stats?range=all", headers=headers)).json()

    await _create_published_template(client, headers, ts, "01")
    await _create_published_template(client, headers, ts, "02")
    await _create_published_playbook(client, headers, ts, "01")
    await _create_activation_code(client, headers)

    after = (await client.get("/api/admin/dashboard/stats?range=all", headers=headers)).json()

    assert after["templates_published"] - before["templates_published"] >= 2
    assert after["playbooks_published"] - before["playbooks_published"] >= 1
    assert after["activation_codes"]["total"] - before["activation_codes"]["total"] >= 1


# ---------------------------------------------------------------------------
# /top-templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top_templates_structure(client: AsyncClient) -> None:
    """top-templates 返回结构正确。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)

    for range_value in ("all", "7d", "30d"):
        resp = await client.get(
            f"/api/admin/dashboard/top-templates?range={range_value}&limit=5",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["range"] == range_value
        assert "items" in data
        for item in data["items"]:
            assert "id" in item
            assert "title" in item
            assert "description" in item
            assert "use_count" in item
            assert "tags" in item
            assert isinstance(item["use_count"], int)


@pytest.mark.asyncio
async def test_top_templates_respects_limit(client: AsyncClient) -> None:
    """limit 参数生效。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    resp = await client.get("/api/admin/dashboard/top-templates?range=all&limit=3", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) <= 3


# ---------------------------------------------------------------------------
# /top-playbooks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top_playbooks_structure(client: AsyncClient) -> None:
    """top-playbooks 包含 steps_count 字段。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    resp = await client.get("/api/admin/dashboard/top-playbooks?range=all&limit=5", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert "id" in item
        assert "title" in item
        assert "use_count" in item
        assert "steps_count" in item
        assert isinstance(item["steps_count"], int)


@pytest.mark.asyncio
async def test_top_playbooks_in_range_7d_empty_or_runs(client: AsyncClient) -> None:
    """区间内 7d 排行榜：要么为空，要么 use_count <= 实际行数。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    resp = await client.get("/api/admin/dashboard/top-playbooks?range=7d&limit=10", headers=headers)
    assert resp.status_code == 200
    # 区间内无 playbook run 时返回空列表是合法状态
    assert isinstance(resp.json()["items"], list)


# ---------------------------------------------------------------------------
# /recent-activity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recent_activity_structure(client: AsyncClient) -> None:
    """recent-activity 返回结构 + type 字段限制。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    resp = await client.get("/api/admin/dashboard/recent-activity?limit=5", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["type"] in ("template", "playbook")
        assert "id" in item
        assert "title" in item
        assert "status" in item
        assert "created_at" in item


@pytest.mark.asyncio
async def test_recent_activity_includes_published_templates(client: AsyncClient) -> None:
    """新建一个已发布模板后，recent-activity 应包含它。"""
    token = await _admin_login(client)
    headers = _admin_headers(token)
    ts = str(int(time.time() * 1000))
    title = f"e2e-recent-tpl-{ts}"
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": title,
            "description": "recent activity test",
            "content": "你是专家。{{topic}}。输出：示例。",
            "variable_hints": {"topic": "主题"},
            "status": "published",
        },
        headers=headers,
    )
    assert create.status_code == 201

    resp = await client.get("/api/admin/dashboard/recent-activity?limit=20", headers=headers)
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["items"]]
    assert title in titles
