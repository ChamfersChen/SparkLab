"""工作流 (Playbook) 模型。

一个工作流 = 一组按顺序执行的模板步骤（playbook_steps），可关联标签。
工作流本身只有一个 `content` 字段 (Markdown),运行期作为「全局上下文」展示在 Run 页顶部。
状态机与 Template 一致：draft / published / archived。
"""

import enum

from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sparklab.models.base import Base, TimestampMixin


class PlaybookStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PlaybookTag(Base):
    """工作流与标签的多对多关联表。"""

    __tablename__ = "playbook_tags"

    playbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playbooks.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


class PlaybookStep(Base):
    """工作流的一个步骤。自带 prompt content (Markdown + {{var}} + {{prev_output}})。"""

    __tablename__ = "playbook_steps"
    __table_args__ = (
        UniqueConstraint("playbook_id", "step_order", name="uq_playbook_steps_playbook_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 步骤自带 prompt (Markdown), 支持 {{变量}} 与特殊占位符 {{prev_output}}
    content: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    def __repr__(self) -> str:
        return f"<PlaybookStep id={self.id} playbook_id={self.playbook_id} order={self.step_order} name={self.name!r}>"


class Playbook(Base, TimestampMixin):
    __tablename__ = "playbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # 单一内容字段 (Markdown),作为「全局上下文」在运行页顶部展示
    content: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    # 工作流级变量提示（JSON 格式：{"变量名": "提示文案"}）
    variable_hints: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[PlaybookStatus] = mapped_column(
        Enum(PlaybookStatus, name="playbook_status", create_constraint=True),
        nullable=False,
        default=PlaybookStatus.DRAFT,
    )
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 关联
    steps: Mapped[list["PlaybookStep"]] = relationship(
        "PlaybookStep",
        cascade="all, delete-orphan",
        order_by="PlaybookStep.step_order",
        lazy="selectin",
    )
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="playbook_tags",
        backref="playbooks",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Playbook id={self.id} title={self.title!r} status={self.status.value}>"
