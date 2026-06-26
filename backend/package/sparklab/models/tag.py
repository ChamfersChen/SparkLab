import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from sparklab.models.base import Base, TimestampMixin


class TagCategory(enum.StrEnum):
    PLATFORM = "platform"
    CONTENT_TYPE = "content_type"
    INDUSTRY = "industry"


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[TagCategory] = mapped_column(SAEnum(TagCategory), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
