"""收藏模型 — 支持模板和工作流两种收藏类型。"""

import enum

from sqlalchemy import Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from sparklab.models.base import Base, TimestampMixin


class FavoriteTargetType(str, enum.Enum):
    """收藏目标类型。"""

    TEMPLATE = "template"
    PLAYBOOK = "playbook"


class Favorite(Base, TimestampMixin):
    """用户收藏记录。联合唯一约束: (user_id, target_type, target_id)。"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_favorite_target"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[FavoriteTargetType] = mapped_column(
        Enum(
            FavoriteTargetType,
            name="favorite_target_type",
            create_constraint=False,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
