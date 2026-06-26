"""SparkLab API 应用入口。

集中负责：
- FastAPI 应用组装
- CORS（开发期默认放行前端开发服务器）
- 登录限流（每 IP 60 秒最多 10 次 /api/auth/login 与 /api/activation/activate POST）
- 路由统一挂载到 /api
"""

import asyncio
import os
import sys
import time
from collections import defaultdict, deque

# Windows 下 asyncpg 需要 SelectorEventLoop，必须在导入 FastAPI 前设置
if sys.platform == "win32":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.append(r"E:\lcfc\repositories\MOM-Know\backend\package")  # 替换为你的实际路径
sys.path.append(r"/app/package")  # 替换为你的实际路径

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sparklab.utils.logger import setup_logging
from starlette.middleware.base import BaseHTTPMiddleware

from server.routers import router
from server.utils.access_log_middleware import AccessLogMiddleware
from server.utils.lifespan import lifespan

setup_logging()

RATE_LIMIT_MAX_ATTEMPTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_ENDPOINTS = {
    ("/api/auth/login", "POST"),
    ("/api/activation/activate", "POST"),
}
DEFAULT_DEV_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("SPARKLAB_CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if origins:
        return origins
    env = (os.getenv("SPARKLAB_ENV") or "development").strip().lower()
    if env in {"production", "prod"}:
        return []
    return list(DEFAULT_DEV_CORS_ORIGINS)


app = FastAPI(lifespan=lifespan, title="SparkLab API", version="0.1.0")
app.include_router(router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# ---------------------------------------------------------------------------
# 登录限流中间件
# ---------------------------------------------------------------------------
_login_attempts: defaultdict[str, deque[float]] = defaultdict(deque)
_attempt_lock = asyncio.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        sig = (request.url.path.rstrip("/") or "/", request.method.upper())
        if sig in RATE_LIMIT_ENDPOINTS:
            ip = _client_ip(request)
            now = time.monotonic()
            async with _attempt_lock:
                hist = _login_attempts[ip]
                while hist and now - hist[0] > RATE_LIMIT_WINDOW_SECONDS:
                    hist.popleft()
                if len(hist) >= RATE_LIMIT_MAX_ATTEMPTS:
                    retry_after = int(max(1, RATE_LIMIT_WINDOW_SECONDS - (now - hist[0])))
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "请求过于频繁，请稍后再试"},
                        headers={"Retry-After": str(retry_after)},
                    )
                hist.append(now)
            response = await call_next(request)
            # 成功后清空该 IP 的失败计数
            if response.status_code < 400:
                async with _attempt_lock:
                    _login_attempts.pop(ip, None)
            return response
        return await call_next(request)


app.add_middleware(AccessLogMiddleware)
app.add_middleware(LoginRateLimitMiddleware)


if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=5050,
        reload=True,
        reload_dirs=["server", "package"],
    )
