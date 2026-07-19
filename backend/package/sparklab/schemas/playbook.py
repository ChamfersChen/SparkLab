"""工作流 (Playbook) 的 Pydantic 请求/响应模型。

约定:
  - TagInfo 是嵌入关系(与 template.py 中保持同名同构)
  - PlaybookStepItem 是嵌入的步骤项
  - PlaybookUpdateRequest 中所有字段 Optional;steps 字段若提供则为「整组替换」而非增量
  - variable_hints 复用 template.py 的 JSON 解析模式
  - 步骤不再关联 Template: 自带 content (Markdown + {{var}} + {{prev_output}})
  - 运行期 {{prev_output}} 由前端把上一步 AI 平台返回结果粘回,放在 PlaybookStepOutput.prev_output
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PlaybookStatusLiteral = Literal["draft", "published", "archived"]


class TagInfo(BaseModel):
    """标签的简洁表示（嵌入工作流响应中）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v):
        return v.value if hasattr(v, "value") else v


class PlaybookStepItem(BaseModel):
    """工作流中一个步骤的对外表示。"""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    step_order: int
    name: str = ""
    description: str | None = None
    # 步骤自带 prompt (Markdown)。支持 {{var}} 与特殊占位符 {{prev_output}}
    content: str = ""


class PlaybookResponse(BaseModel):
    """工作流详情。"""

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
    is_private: bool = False
    steps: list[PlaybookStepItem] = []
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


class PlaybookListResponse(BaseModel):
    items: list[PlaybookResponse]
    total: int


class PlaybookCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=500)
    content: str = ""
    variable_hints: dict[str, str] | None = None
    # steps 至少 1 项;每步自带 content
    steps: list[PlaybookStepItem] = Field(..., min_length=1)
    tag_ids: list[int] = []
    status: PlaybookStatusLiteral = "draft"
    is_private: bool = False


class PlaybookUpdateRequest(BaseModel):
    """全字段可选;steps 若提供则为「整组替换」。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    variable_hints: dict[str, str] | None = None
    steps: list[PlaybookStepItem] | None = Field(default=None, min_length=1)
    tag_ids: list[int] | None = None
    status: PlaybookStatusLiteral | None = None


class PlaybookStatusChangeRequest(BaseModel):
    status: PlaybookStatusLiteral


# ---------------------------------------------------------------------------
# 运行相关
# ---------------------------------------------------------------------------


class PlaybookStepOutput(BaseModel):
    """用户在某一步提交的内容。

    prev_output 是该步骤的「上游输入」: 用户在 AI 平台提问后粘回的结果,
    会被注入到该步骤 content 的 {{prev_output}} 占位符里。
    form_values 是该步骤自己的变量填写值。
    """

    step_order: int = Field(..., ge=0)
    form_values: dict[str, str] = Field(default_factory=dict)
    prev_output: str | None = None


class PlaybookRunRequest(BaseModel):
    """运行工作流：用户提交所有步骤的填写值。"""

    form_values: dict[str, str] = Field(default_factory=dict, description="工作流级变量")
    step_outputs: list[PlaybookStepOutput] = Field(default_factory=list)


class PlaybookRunStep(BaseModel):
    """运行后某一步的渲染结果。"""

    step_order: int
    name: str
    # 替换 {{var}} + {{prev_output}} 后的最终内容(Markdown)
    filled_content: str
    # 本步渲染时是否真的注入了 prev_output(只有当 content 含 {{prev_output}} 且上游有结果时才为 true)
    prev_output_injected: bool = False


class PlaybookRunResponse(BaseModel):
    playbook_id: int
    playbook_title: str
    # 完整渲染后的 prompt：工作流 content (替换变量) + 每步 content (替换变量) 用 \n\n---\n\n 串起来
    final_prompt: str
    steps: list[PlaybookRunStep]


# ---------------------------------------------------------------------------
# 运行记录保存（个人中心 / 我的运行记录）
# ---------------------------------------------------------------------------


def _parse_form_values_json(v):
    """字段 validator: 把存盘的 JSON 字符串解析为 dict (None / dict 透传)."""
    if v is None or v == "":
        return {}
    if isinstance(v, dict):
        return v
    import json

    try:
        result = json.loads(v)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


class PlaybookRunStepItem(BaseModel):
    """一次运行中某一步的对外表示 (列表 + 详情共用)."""

    model_config = ConfigDict(from_attributes=True)

    step_order: int
    step_name: str
    user_output: str | None = None
    # 原始 (Pydantic input) 是 dict, DB 取出来是 JSON 字符串, 由 validator 解析
    form_values: dict[str, str] = Field(default_factory=dict)
    # v4: server 现算的 step 补充后 prompt (content + {{var}} + {{prev_output}} 替换后)
    filled_prompt: str | None = None

    @field_validator("form_values", mode="before")
    @classmethod
    def parse_form_values(cls, v):
        return _parse_form_values_json(v)


class PlaybookRunSummary(BaseModel):
    """列表项 — 不带 steps 详情, 只给统计."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    playbook_id: int
    playbook_title: str
    title: str | None = None
    created_at: datetime
    # 这次运行中 step 总数 (该 playbook 当时)
    step_count: int = 0
    # 实际粘回 AI 结果的 step 数 (user_output 非空)
    filled_step_count: int = 0
    # v4: 用户是否在右栏填了"最终结果"
    has_final_result: bool = False


class PlaybookRunDetail(BaseModel):
    """详情 — 含 steps."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    playbook_id: int
    playbook_title: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    step_count: int = 0
    filled_step_count: int = 0
    has_final_result: bool = False
    # v4: 用户在三栏右栏填的最终结果 Markdown 源文本
    final_result: str | None = None
    steps: list[PlaybookRunStepItem] = []


class PlaybookRunCreateRequest(BaseModel):
    """保存一次运行的请求体."""

    playbook_id: int
    title: str | None = Field(default=None, max_length=200)
    # v4: 用户在三栏页右栏填的"最终结果" (Markdown 源文本, 渲染时后端做)
    final_result: str | None = None
    # steps 仍传 user_output + form_values, server 端算 filled_prompt 后存盘
    steps: list[PlaybookRunStepItem] = Field(..., min_length=1)


class PlaybookRunListResponse(BaseModel):
    items: list[PlaybookRunSummary]
    total: int
