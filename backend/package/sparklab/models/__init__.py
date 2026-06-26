"""SQLAlchemy 模型层。

各业务表的模型在此包下按领域拆分（user.py / template.py / playbook.py ...），
统一从 base.Base 继承。Alembic env.py 通过 `from sparklab.models import *`
扫描所有模型以自动生成迁移。
"""

from sparklab.models.activation_code import ActivationCode, ActivationCodeStatus
from sparklab.models.base import Base, TimestampMixin
from sparklab.models.tag import Tag, TagCategory
from sparklab.models.template import Template, TemplateStatus, TemplateTag
from sparklab.models.user import User, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "ActivationCode",
    "ActivationCodeStatus",
    "Tag",
    "TagCategory",
    "Template",
    "TemplateStatus",
    "TemplateTag",
]
