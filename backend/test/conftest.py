"""pytest 全局 fixture。

- `client` fixture 提供 httpx AsyncClient，绑定到内存中的 FastAPI 应用，
  无需启动真实 uvicorn，适合 e2e 测试。
- 测试用例假设 .env 已加载（容器内由 docker-compose 注入；本地裸跑可手动 export）。
"""

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """提供绑定到 FastAPI app 的异步 HTTP 客户端。

    注意：测试会触发 lifespan（含 Alembic 迁移 + DB/Redis 连接验证），
    因此需要 postgres + redis 容器在运行。
    """
    # 延迟导入：让 .env 在测试参数化之前先被 settings 读完
    from server.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with app.router.lifespan_context(app):
            yield ac
