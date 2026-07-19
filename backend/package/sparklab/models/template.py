"""模板模型。

模板只保留一个 `content` 字段(Markdown 文本),支持 `{{变量名}}` 占位符。
运行期由用户填变量,后端做替换,再渲染成最终 prompt。
通过 `template_tags` 与标签建立多对多关联。
"""

import enum

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sparklab.models.base import Base, TimestampMixin


class TemplateStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TemplateTag(Base):
    """模板与标签的多对多关联表。"""

    __tablename__ = "template_tags"

    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # 单一内容字段 (Markdown),支持 {{变量名}} 占位符
    content: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")

    # 变量填写提示（JSON 格式：{"变量名": "提示文案"}）
    variable_hints: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus, name="template_status", create_constraint=True),
        nullable=False,
        default=TemplateStatus.DRAFT,
    )
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    creator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # 是否为私有模板（普通用户创建为私有，管理员创建为公开）
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # 关联
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="template_tags",
        backref="templates",
        lazy="selectin",
    )
    runs: Mapped[list["TemplateRun"]] = relationship(
        "TemplateRun",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} title={self.title!r} status={self.status.value}>"


class TemplateRun(Base, TimestampMixin):
    """模板的一次使用记录 — 用户在个人中心回看。

    保存用户填写的变量值、生成的最终 prompt。
    """

    __tablename__ = "template_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("templates.id", ondelete="CASCADE"), nullable=False)
    # 用户自定义标题; 默认值由 service 层根据 template.title + 时间戳生成
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 生成的最终 prompt
    generated_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 用户填写的变量值 (JSON 快照)
    form_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI 平台返回的结果 (用户粘贴)
    ai_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关联
    template: Mapped["Template"] = relationship(
        "Template",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<TemplateRun id={self.id} user_id={self.user_id} template_id={self.template_id}>"
