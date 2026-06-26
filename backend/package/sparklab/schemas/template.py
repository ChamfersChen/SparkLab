from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TagInfo(BaseModel):
    """标签的简洁表示（嵌入模板响应中）。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v):
        return v.value if hasattr(v, "value") else v


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    role: str
    goal: str
    input: str
    output: str
    example: str
    variable_hints: dict[str, str] | None = None
    status: str
    use_count: int
    creator_id: int | None = None
    tags: list[TagInfo] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v):
        return v.value if hasattr(v, "value") else v

    @field_validator("variable_hints", mode="before")
    @classmethod
    def parse_hints(cls, v):
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        import json
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return None


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int


class TemplateCreateRequest(BaseModel):
    title: str
    description: str
    role: str
    goal: str
    input: str
    output: str
    example: str
    variable_hints: dict[str, str] | None = None
    tag_ids: list[int] = []
    status: str = "draft"


class TemplateUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    role: str | None = None
    goal: str | None = None
    input: str | None = None
    output: str | None = None
    example: str | None = None
    variable_hints: dict[str, str] | None = None
    tag_ids: list[int] | None = None
    status: str | None = None


class TemplateStatusChangeRequest(BaseModel):
    status: str


class TemplateListParams(BaseModel):
    search: str | None = None
    tag_ids: list[int] | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 20


class FillDataResponse(BaseModel):
    """模板填写页数据。"""
    model_config = ConfigDict(from_attributes=True)

    template_id: int
    title: str
    description: str
    role: str
    goal: str
    input: str
    output: str
    example: str
    variable_hints: dict[str, str] = {}


class VariableExtractResponse(BaseModel):
    """变量提取结果。"""
    variables: list[str]
