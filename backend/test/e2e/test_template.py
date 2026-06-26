"""模板管理的 e2e 测试（用户端 + 管理后台）。"""
import time

import pytest
from httpx import AsyncClient
from sparklab.config import get_settings


@pytest.mark.asyncio
async def test_templates_requires_auth(client: AsyncClient) -> None:
    """未登录访问 /api/templates 应返回 401。"""
    resp = await client.get("/api/templates")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_template_crud(client: AsyncClient) -> None:
    """管理员可以创建、查询、编辑、下线模板。"""
    settings = get_settings()
    login_resp = await client.post(
        "/api/auth/login",
        json={
            "username": settings.initial_superadmin_username,
            "password": settings.initial_superadmin_password,
        },
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    ts = str(int(time.time()))

    # Create template
    create_resp = await client.post(
        "/api/admin/templates",
        json={
            "title": f"e2e-template-{ts}",
            "description": "e2e test template",
            "role": "你是一名资深文案专家",
            "goal": "帮助用户撰写营销文案",
            "input": "产品名称：{{产品名称}}，卖点：{{卖点}}",
            "output": "输出一段 200 字的营销文案",
            "example": "这是示例效果",
            "variable_hints": {"产品名称": "请输入产品完整名称", "卖点": "列出2-3个核心卖点"},
            "status": "published",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    template_id = create_resp.json()["id"]
    assert create_resp.json()["title"] == f"e2e-template-{ts}"
    assert create_resp.json()["status"] == "published"
    assert create_resp.json()["variable_hints"]["产品名称"] == "请输入产品完整名称"

    # List templates (admin)
    list_resp = await client.get(
        "/api/admin/templates?page=1&page_size=20",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    names = [i["title"] for i in list_resp.json()["items"]]
    assert f"e2e-template-{ts}" in names

    # List templates (user) — should be visible since published
    user_list = await client.get(
        "/api/templates?page=1&page_size=20",
        headers=headers,
    )
    assert user_list.status_code == 200
    user_names = [i["title"] for i in user_list.json()["items"]]
    assert f"e2e-template-{ts}" in user_names

    # Get template detail
    detail_resp = await client.get(
        f"/api/templates/{template_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["title"] == f"e2e-template-{ts}"
    assert "产品名称" in detail_resp.json()["input"]

    # Get fill data
    fill_resp = await client.get(
        f"/api/templates/{template_id}/fill",
        headers=headers,
    )
    assert fill_resp.status_code == 200
    assert fill_resp.json()["template_id"] == template_id
    assert "产品名称" in fill_resp.json()["variable_hints"]

    # Update template
    update_resp = await client.put(
        f"/api/admin/templates/{template_id}",
        json={"title": f"e2e-updated-{ts}", "description": "updated description"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == f"e2e-updated-{ts}"

    # Change status to draft
    status_resp = await client.put(
        f"/api/admin/templates/{template_id}/status",
        json={"status": "draft"},
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "draft"

    # User should no longer see it
    user_list2 = await client.get(
        "/api/templates?page=1&page_size=20",
        headers=headers,
    )
    user_names2 = [i["title"] for i in user_list2.json()["items"]]
    assert f"e2e-updated-{ts}" not in user_names2

    # Increment use count
    use_resp = await client.post(
        f"/api/templates/{template_id}/use",
        headers=headers,
    )
    assert use_resp.status_code == 200

    # Verify use count incremented
    detail2 = await client.get(
        f"/api/templates/{template_id}",
        headers=headers,
    )
    assert detail2.status_code == 200
    assert detail2.json()["use_count"] >= 1

    # Delete (soft)
    delete_resp = await client.delete(
        f"/api/admin/templates/{template_id}",
        headers=headers,
    )
    assert delete_resp.status_code == 204

    # Verify soft-deleted (archived)
    detail3 = await client.get(
        f"/api/admin/templates/{template_id}",
        headers=headers,
    )
    assert detail3.status_code == 200
    assert detail3.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_user_cannot_access_admin_templates(client: AsyncClient) -> None:
    """普通用户无法访问管理后台模板接口。"""
    ts = str(int(time.time()))
    settings = get_settings()

    # Login as admin
    login_resp = await client.post(
        "/api/auth/login",
        json={
            "username": settings.initial_superadmin_username,
            "password": settings.initial_superadmin_password,
        },
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create activation code
    gen_resp = await client.post(
        "/api/admin/activation-codes/generate",
        json={"count": 1},
        headers=admin_headers,
    )
    code = gen_resp.json()["items"][0]["code"]

    # Register as normal user
    register_resp = await client.post(
        "/api/activation/activate",
        json={
            "code": code,
            "username": f"normal_template_{ts}",
            "password": "test123456",
        },
    )
    assert register_resp.status_code == 200
    user_token = register_resp.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Try accessing admin templates
    resp = await client.get("/api/admin/templates", headers=user_headers)
    assert resp.status_code == 403


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    """登录超管并返回 Bearer 头。"""
    settings = get_settings()
    resp = await client.post(
        "/api/auth/login",
        json={
            "username": settings.initial_superadmin_username,
            "password": settings.initial_superadmin_password,
        },
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.mark.asyncio
async def test_create_template_rejects_invalid_status(client: AsyncClient) -> None:
    """创建模板时 status 非法值应被 422 拒绝。"""
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/admin/templates",
        json={
            "title": "x",
            "description": "x",
            "role": "x",
            "goal": "x",
            "input": "x",
            "output": "x",
            "example": "x",
            "status": "deleted",  # 非法值
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_change_status_rejects_invalid_value(client: AsyncClient) -> None:
    """状态切换接口 status 非法值应被 422 拒绝。"""
    headers = await _admin_headers(client)
    # 准备一个模板
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-status",
            "description": "t",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
        },
        headers=headers,
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    resp = await client.put(
        f"/api/admin/templates/{tid}/status",
        json={"status": "removed"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_template_rejects_invalid_tag_ids(client: AsyncClient) -> None:
    """创建模板时 tag_ids 含不存在的 ID 应被 400 拒绝。"""
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-bad-tag",
            "description": "t",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
            "tag_ids": [999_999],
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "999999" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_create_template_rejects_empty_title(client: AsyncClient) -> None:
    """空 title 应被 422 拒绝，且 detail 必须是 Pydantic 标准数组结构。"""
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/admin/templates",
        json={
            "title": "",
            "description": "t",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
        },
        headers=headers,
    )
    assert resp.status_code == 422
    body = resp.json()
    assert isinstance(body["detail"], list)
    assert body["detail"][0]["loc"][-1] == "title"


@pytest.mark.asyncio
async def test_create_template_rejects_uncovered_variables(client: AsyncClient) -> None:
    """Input 段出现 {{X}} 但 variable_hints 没配 X → 400。"""
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-coverage",
            "description": "d",
            "role": "r",
            "goal": "g",
            "input": "产品：{{产品名称}}，卖点：{{卖点}}",
            "output": "o",
            "example": "e",
            "variable_hints": {"产品名称": "请输入完整产品名"},
            # 注意：刻意不配"卖点"
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "卖点" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_update_template_rejects_uncovered_variables(client: AsyncClient) -> None:
    """update 时若改 input 引入新变量但 hints 未覆盖 → 400。"""
    headers = await _admin_headers(client)
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-upd-coverage",
            "description": "d",
            "role": "r",
            "goal": "g",
            "input": "原内容：{{A}}",
            "output": "o",
            "example": "e",
            "variable_hints": {"A": "h"},
        },
        headers=headers,
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    resp = await client.put(
        f"/api/admin/templates/{tid}",
        json={
            "input": "新内容：{{A}}，副标题：{{B}}",
            "variable_hints": {"A": "h"},
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "B" in resp.json()["detail"]


async def _create_user_and_get_headers(
    client: AsyncClient, admin_headers: dict[str, str], username: str
) -> dict[str, str]:
    """用管理员生成激活码、激活新用户，返回新用户 Bearer 头。"""
    gen = await client.post(
        "/api/admin/activation-codes/generate",
        json={"count": 1},
        headers=admin_headers,
    )
    assert gen.status_code == 200
    code = gen.json()["items"][0]["code"]
    act = await client.post(
        "/api/activation/activate",
        json={"code": code, "username": username, "password": "test123456"},
    )
    assert act.status_code == 200
    return {"Authorization": f"Bearer {act.json()['token']}"}


@pytest.mark.asyncio
async def test_draft_template_invisible_to_other_users(client: AsyncClient) -> None:
    """草稿模板对非作者普通用户 → 404。"""
    admin_headers = await _admin_headers(client)
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-draft-private",
            "description": "d",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
            "status": "draft",
        },
        headers=admin_headers,
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    other_headers = await _create_user_and_get_headers(
        client, admin_headers, "other_user_draft"
    )
    resp = await client.get(f"/api/templates/{tid}", headers=other_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_archived_template_invisible_to_other_users(client: AsyncClient) -> None:
    """已归档模板对非作者普通用户 → 404。"""
    admin_headers = await _admin_headers(client)
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-arch-private",
            "description": "d",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
            "status": "published",
        },
        headers=admin_headers,
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    # 归档
    arch = await client.put(
        f"/api/admin/templates/{tid}/status",
        json={"status": "archived"},
        headers=admin_headers,
    )
    assert arch.status_code == 200

    other_headers = await _create_user_and_get_headers(
        client, admin_headers, "other_user_arch"
    )
    resp = await client.get(f"/api/templates/{tid}", headers=other_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_draft_template_visible_to_author(client: AsyncClient) -> None:
    """草稿模板对作者本人 → 200。"""
    admin_headers = await _admin_headers(client)
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-draft-self",
            "description": "d",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
            "status": "draft",
        },
        headers=admin_headers,
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    resp = await client.get(f"/api/templates/{tid}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_draft_template_visible_via_admin_endpoint_to_any_admin(
    client: AsyncClient,
) -> None:
    """任意管理员可经 /api/admin/templates/{id} 访问草稿（不走用户端可见性）。"""
    admin_headers = await _admin_headers(client)
    create = await client.post(
        "/api/admin/templates",
        json={
            "title": "t-admin-preview",
            "description": "d",
            "role": "r",
            "goal": "g",
            "input": "i",
            "output": "o",
            "example": "e",
            "status": "draft",
        },
        headers=admin_headers,
    )
    assert create.status_code == 201
    tid = create.json()["id"]

    # 用第二个普通用户升级为管理员不易,这里直接复用同一个超管(creator=超管自己)从管理端访问
    resp = await client.get(f"/api/admin/templates/{tid}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"
