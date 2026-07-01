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


class PlaybookRun(Base, TimestampMixin):
    """工作流的一次"完整跑完"记录 — 用户在个人中心回看。

    每条记录包含 N 个 PlaybookRunStep, 每步保存当时的 step_name 快照 + 用户粘回的
    AI 结果 (user_output)。step_name 是快照, 即便工作流被改名/删除, 历史记录不受影响。
    """

    __tablename__ = "playbook_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    playbook_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False
    )
    # 用户自定义标题; 默认值由 service 层根据 playbook.title + 时间戳生成
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # v4: 用户在三栏页右栏填的"最终结果" (Markdown 源文本)
    final_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    playbook: Mapped["Playbook"] = relationship(
        "Playbook",
        lazy="joined",
    )

    steps: Mapped[list["PlaybookRunStep"]] = relationship(
        "PlaybookRunStep",
        cascade="all, delete-orphan",
        order_by="PlaybookRunStep.step_order",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PlaybookRun id={self.id} user_id={self.user_id} playbook_id={self.playbook_id}>"


class PlaybookRunStep(Base, TimestampMixin):
    """一次运行中某一步的快照。"""

    __tablename__ = "playbook_run_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("playbook_runs.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    # 步骤名快照 (原 step 改名不影响历史)
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 用户粘回的 AI 回答, NULL = 该步未粘回
    user_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 本步用户填写的变量 (JSON 快照, 供回看)
    form_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v4: server 用 content + form_values + 上一步 user_output 现算的补充后 prompt 快照
    filled_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PlaybookRunStep id={self.id} run_id={self.run_id} order={self.step_order}>"
