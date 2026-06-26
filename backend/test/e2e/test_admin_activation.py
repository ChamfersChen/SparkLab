"""管理后台激活码接口的 e2e 测试。

测试之前必须先通过管理员登录获取令牌。
"""
import time

import pytest
from httpx import AsyncClient

from sparklab.config import get_settings


@pytest.mark.asyncio
async def test_admin_list_codes_requires_auth(client: AsyncClient) -> None:
    """未登录访问 /api/admin/activation-codes 应返回 401。"""
    resp = await client.get("/api/admin/activation-codes")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_generate_and_toggle_code(client: AsyncClient) -> None:
    """超级管理员可以生成、查询、复制、禁用/启用激活码。"""
    settings = get_settings()
    # Login
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

    # Generate 3 codes
    gen_resp = await client.post(
        "/api/admin/activation-codes/generate",
        json={"count": 3, "note": "e2e test"},
        headers=headers,
    )
    assert gen_resp.status_code == 200
    data = gen_resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    code_id = data["items"][0]["id"]
    code_str = data["items"][0]["code"]
    assert data["items"][0]["status"] == "unused"

    # List codes
    list_resp = await client.get(
        "/api/admin/activation-codes?page=1&page_size=20",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 3

    # Search by note
    search_resp = await client.get(
        "/api/admin/activation-codes?search=e2e+test",
        headers=headers,
    )
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] >= 3

    # Search by code
    code_search = await client.get(
        f"/api/admin/activation-codes?search={code_str[:4]}",
        headers=headers,
    )
    assert code_search.status_code == 200
    assert code_search.json()["total"] >= 1

    # Filter by status
    unused_resp = await client.get(
        "/api/admin/activation-codes?status=unused",
        headers=headers,
    )
    assert unused_resp.status_code == 200

    # Disable a code
    toggle_resp = await client.put(
        f"/api/admin/activation-codes/{code_id}/toggle",
        headers=headers,
    )
    assert toggle_resp.status_code == 200
    assert "已禁用" in toggle_resp.json()["message"]

    # Verify disabled
    status_check = await client.get(
        f"/api/admin/activation-codes?search={code_str}",
        headers=headers,
    )
    assert status_check.status_code == 200
    items = status_check.json()["items"]
    disabled = [i for i in items if i["id"] == code_id]
    assert len(disabled) == 1
    assert disabled[0]["status"] == "disabled"

    # Re-enable
    toggle_back = await client.put(
        f"/api/admin/activation-codes/{code_id}/toggle",
        headers=headers,
    )
    assert toggle_back.status_code == 200
    assert "已启用" in toggle_back.json()["message"]


@pytest.mark.asyncio
async def test_admin_normal_user_cannot_access(client: AsyncClient) -> None:
    """普通用户无法访问管理后台接口。"""
    ts = str(int(time.time()))
    settings = get_settings()

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

    gen_resp = await client.post(
        "/api/admin/activation-codes/generate",
        json={"count": 1},
        headers=admin_headers,
    )
    code = gen_resp.json()["items"][0]["code"]

    register_resp = await client.post(
        "/api/activation/activate",
        json={
            "code": code,
            "username": f"test_normal_{ts}",
            "password": "test123456",
        },
    )
    assert register_resp.status_code == 200
    user_token = register_resp.json()["token"]

    user_headers = {"Authorization": f"Bearer {user_token}"}
    resp = await client.get("/api/admin/activation-codes", headers=user_headers)
    assert resp.status_code == 403
