from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_active: bool


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user: UserInfo
    token: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v


class ActivationVerifyRequest(BaseModel):
    code: str


class ActivationVerifyResponse(BaseModel):
    valid: bool
    message: str | None = None


class ActivateRequest(BaseModel):
    code: str
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_min_length(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("用户名至少 2 个字符")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v


class ActivateResponse(BaseModel):
    user: UserInfo
    token: str


class MessageResponse(BaseModel):
    message: str


# -- 管理员：激活码管理 --


class ActivationCodeInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    status: str
    note: str | None = None
    user_id: int | None = None
    used_at: datetime | None = None
    created_at: datetime | None = None

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v):
        return v.value if hasattr(v, "value") else v


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class ActivationCodeWithUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    status: str
    note: str | None = None
    user: UserBrief | None = None
    creator: UserBrief | None = None
    used_at: datetime | None = None
    created_at: datetime | None = None

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v):
        return v.value if hasattr(v, "value") else v


class ActivationCodeListResponse(BaseModel):
    items: list[ActivationCodeWithUser]
    total: int


class GenerateCodesRequest(BaseModel):
    count: int = 10
    note: str | None = None

    @field_validator("count")
    @classmethod
    def count_range(cls, v: int) -> int:
        if v < 1:
            raise ValueError("数量至少为 1")
        if v > 100:
            raise ValueError("单次最多生成 100 个")
        return v


class UpdateNoteRequest(BaseModel):
    note: str | None = None
