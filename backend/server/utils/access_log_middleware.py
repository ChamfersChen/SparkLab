"""访问日志中间件 - 记录每次请求的 method/path/status/duration。

仅记录元信息，不记录请求体/响应体，避免密码、Token 等敏感数据落盘。
"""

import time

from sparklab.utils.logger import access_logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        access_logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
