"""模板模型。

模板只保留一个 `content` 字段(Markdown 文本),支持 `{{变量名}}` 占位符。
运行期由用户填变量,后端做替换,再渲染成最终 prompt。
通过 `template_tags` 与标签建立多对多关联。
"""

import enum

from sqlalchemy import (
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

    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("templates.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )


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
    creator_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 关联
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="template_tags",
        backref="templates",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} title={self.title!r} status={self.status.value}>"
