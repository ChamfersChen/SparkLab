"""收藏 (Favorite) 的 Pydantic 请求/响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

FavoriteTargetTypeLiteral = Literal["template", "playbook"]


class FavoriteResponse(BaseModel):
    """收藏项响应 — 包含目标的基本信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: str
    target_id: int
    title: str = ""
    description: str = ""
    created_at: datetime | None = None

    @field_validator("target_type", mode="before")
    @classmethod
    def coerce_target_type(cls, v):
        return v.value if hasattr(v, "value") else v


class FavoriteListResponse(BaseModel):
    items: list[FavoriteResponse]
    total: int


class FavoriteCreateRequest(BaseModel):
    target_type: FavoriteTargetTypeLiteral = Field(..., description="收藏目标类型: template 或 playbook")
    target_id: int = Field(..., gt=0, description="收藏目标 ID")
