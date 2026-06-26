"""系统级接口的 e2e 测试：/api/system/health 与 /api/system/version。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """/api/system/health 应返回 200 + {'status': 'ok'}。"""
    resp = await client.get("/api/system/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_version_returns_current(client: AsyncClient) -> None:
    """/api/system/version 应返回当前包版本。"""
    from sparklab import __version__

    resp = await client.get("/api/system/version")
    assert resp.status_code == 200
    assert resp.json() == {"version": __version__}
