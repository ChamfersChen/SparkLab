from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    sort_order: int
    created_at: datetime | None = None

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v):
        return v.value if hasattr(v, "value") else v


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int


class TagCreateRequest(BaseModel):
    name: str
    category: str
    sort_order: int = 0


class TagUpdateRequest(BaseModel):
    name: str | None = None
    sort_order: int | None = None
