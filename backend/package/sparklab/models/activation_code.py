import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sparklab.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from sparklab.models.user import User


class ActivationCodeStatus(enum.StrEnum):
    UNUSED = "unused"
    USED = "used"
    DISABLED = "disabled"


class ActivationCode(Base, TimestampMixin):
    __tablename__ = "activation_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(14), unique=True, nullable=False, index=True)
    status: Mapped[ActivationCodeStatus] = mapped_column(
        SAEnum(ActivationCodeStatus), default=ActivationCodeStatus.UNUSED, nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    creator: Mapped["User | None"] = relationship(foreign_keys=[creator_id])
