"""SQLAlchemy 模型基类与通用 Mixin。"""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """所有 SparkLab 业务模型的统一基类。"""


class TimestampMixin:
    """提供 created_at / updated_at 列。

    使用方式：
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            ...
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
