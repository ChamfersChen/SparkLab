"""sparklab.utils.logger 的单元测试。"""

import logging

from sparklab.utils.logger import access_logger, logger, setup_logging


def test_loggers_are_exported() -> None:
    """业务 logger 与访问 logger 都应可导入。"""
    assert logger.name == "sparklab"
    assert access_logger.name == "sparklab.access"


def test_access_logger_is_child_of_business_logger() -> None:
    """access logger 是 sparklab logger 的子 logger，可继承配置。"""
    assert access_logger.name.startswith(logger.name + ".")


def test_setup_logging_is_idempotent() -> None:
    """setup_logging 多次调用不应重复添加 handler。"""
    setup_logging()
    first_count = len(logging.getLogger().handlers)
    setup_logging()
    second_count = len(logging.getLogger().handlers)
    assert first_count == second_count
