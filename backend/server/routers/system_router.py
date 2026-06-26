"""系统级接口：健康检查、版本号等。"""

from fastapi import APIRouter
from sparklab import __version__

system = APIRouter(prefix="/system", tags=["system"])


@system.get("/health")
async def health_check() -> dict:
    """轻量健康检查 - 不查 DB，仅证明进程可响应。"""
    return {"status": "ok"}


@system.get("/version")
async def version() -> dict:
    """返回当前后端版本号。"""
    return {"version": __version__}
