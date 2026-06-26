"""标签管理的 e2e 测试（用户端 + 管理后台）。"""
import time

import pytest
from httpx import AsyncClient

from sparklab.config import get_settings


@pytest.mark.asyncio
async def test_tags_requires_auth(client: AsyncClient) -> None:
    """未登录访问 /api/tags 应返回 401。"""
    resp = await client.get("/api/tags")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_tag_crud(client: AsyncClient) -> None:
    """管理员可以创建、查询、编辑、删除标签。"""
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

    # 普通用户访问 admin 标签接口应 403
    admin_list = await client.get("/api/admin/tags", headers=headers)
    assert admin_list.status_code == 200

    # Create
    create_resp = await client.post(
        "/api/admin/tags",
        json={"name": f"e2e-test-{ts}", "category": "platform", "sort_order": 99},
        headers=headers,
    )
    assert create_resp.status_code == 201
    tag_id = create_resp.json()["id"]
    assert create_resp.json()["name"] == f"e2e-test-{ts}"

    # List with category filter
    list_resp = await client.get(
        "/api/admin/tags?category=platform",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1
    names = [i["name"] for i in list_resp.json()["items"]]
    assert f"e2e-test-{ts}" in names

    # Update
    update_resp = await client.put(
        f"/api/admin/tags/{tag_id}",
        json={"name": f"e2e-test-updated-{ts}", "sort_order": 50},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == f"e2e-test-updated-{ts}"
    assert update_resp.json()["sort_order"] == 50

    # Delete
    delete_resp = await client.delete(f"/api/admin/tags/{tag_id}", headers=headers)
    assert delete_resp.status_code == 204

    # Verify deleted
    list_after = await client.get(
        "/api/admin/tags?category=platform",
        headers=headers,
    )
    names_after = [i["name"] for i in list_after.json()["items"]]
    assert f"e2e-test-updated-{ts}" not in names_after


@pytest.mark.asyncio
async def test_user_can_list_tags(client: AsyncClient) -> None:
    """登录后的普通用户可以获取标签列表（分组）。"""
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

    resp = await client.get("/api/tags", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "platform" in data
    assert "content_type" in data
    assert "industry" in data
    assert len(data["platform"]) >= 4


@pytest.mark.asyncio
async def test_duplicate_tag_name(client: AsyncClient) -> None:
    """同一分类下同名标签应返回 409。"""
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

    # First create
    resp1 = await client.post(
        "/api/admin/tags",
        json={"name": "dup-test", "category": "platform"},
        headers=headers,
    )
    tag_id = resp1.json()["id"]

    # Duplicate should fail
    resp2 = await client.post(
        "/api/admin/tags",
        json={"name": "dup-test", "category": "platform"},
        headers=headers,
    )
    assert resp2.status_code == 409

    # Cleanup
    await client.delete(f"/api/admin/tags/{tag_id}", headers=headers)
