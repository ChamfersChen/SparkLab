"""标准 logging 配置。

业务日志：logger = logging.getLogger("sparklab")
访问日志：access_logger = logging.getLogger("sparklab.access")

二者共用同一个格式与 handler，由 setup_logging() 在应用启动时初始化一次。
"""

import logging
import sys

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """配置根 logger - 仅在首次调用时生效。"""
    root = logging.getLogger()
    if root.handlers:
        return  # 已配置过

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn 自身有 logger，统一交给根 logger
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


logger = logging.getLogger("sparklab")
access_logger = logging.getLogger("sparklab.access")
