from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TemplateStatusLiteral = Literal["draft", "published", "archived"]


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
    # 单一 content 字段,支持 Markdown + {{变量名}} 占位符
    content: str
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
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    content: str = ""
    variable_hints: dict[str, str] | None = None
    tag_ids: list[int] = []
    status: TemplateStatusLiteral = "draft"


class TemplateUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    variable_hints: dict[str, str] | None = None
    tag_ids: list[int] | None = None
    status: TemplateStatusLiteral | None = None


class TemplateStatusChangeRequest(BaseModel):
    status: TemplateStatusLiteral


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
    content: str
    variable_hints: dict[str, str] | str = {}

    @field_validator("variable_hints", mode="before")
    @classmethod
    def parse_hints(cls, v):
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        import json
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return {}


class VariableExtractResponse(BaseModel):
    """变量提取结果。"""
    variables: list[str]


# ── 模板使用记录 ──────────────────────────────────────────────────────────


class TemplateRunCreateRequest(BaseModel):
    """保存一次模板使用的请求体."""
    template_id: int
    title: str | None = Field(default=None, max_length=200)
    generated_prompt: str
    form_values: dict[str, str] = Field(default_factory=dict)
    ai_result: str | None = Field(default=None, description="AI 平台返回的结果")


class TemplateRunSummary(BaseModel):
    """列表项 — 不含详细内容."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    template_title: str
    title: str | None = None
    created_at: datetime
    has_prompt: bool = False
    has_result: bool = False


class TemplateRunDetail(BaseModel):
    """详情 — 含生成的 prompt 和变量值."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    template_title: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    generated_prompt: str | None = None
    form_values: dict[str, str] = Field(default_factory=dict)
    ai_result: str | None = None


class TemplateRunListResponse(BaseModel):
    items: list[TemplateRunSummary]
    total: int
