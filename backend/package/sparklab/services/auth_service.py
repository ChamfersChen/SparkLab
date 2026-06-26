from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.auth.activation_code import generate_code
from sparklab.auth.jwt_utils import (
    blacklist_token,
    create_access_token,
    decode_access_token,
    is_token_blacklisted,
)
from sparklab.auth.password import hash_password, verify_password
from sparklab.models.activation_code import ActivationCode, ActivationCodeStatus
from sparklab.models.user import User, UserRole
from sparklab.repositories.activation_code_repository import ActivationCodeRepository
from sparklab.repositories.user_repository import UserRepository
from sparklab.schemas.auth import ActivateResponse, LoginResponse, UserInfo


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.code_repo = ActivationCodeRepository(db)

    @staticmethod
    def _build_login_response(user: User, token: str) -> LoginResponse:
        return LoginResponse(
            user=UserInfo(
                id=user.id,
                username=user.username,
                role=user.role.value,
                is_active=user.is_active,
            ),
            token=token,
        )

    # -- 激活码验证 --

    async def verify_activation_code(self, code: str) -> tuple[bool, str]:
        ac = await self.code_repo.get_by_code(code)
        if ac is None:
            return False, "无效的激活码，请检查链接是否正确，或联系管理员"
        if ac.status == ActivationCodeStatus.USED:
            return False, "该激活码已被使用，请联系管理员获取新的激活码"
        if ac.status == ActivationCodeStatus.DISABLED:
            return False, "该激活码已被禁用，请联系管理员"
        return True, "激活码有效"

    # -- 激活 --

    async def activate(self, code: str, username: str, password: str) -> ActivateResponse:
        valid, msg = await self.verify_activation_code(code)
        if not valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

        ac = await self.code_repo.get_by_code(code)
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被占用",
            )

        pwd_hash = hash_password(password)
        user = await self.user_repo.create(
            username=username,
            password_hash=pwd_hash,
            role=UserRole.USER,
            activation_code_id=ac.id,
        )
        await self.code_repo.mark_used(ac.id, user.id)
        await self.db.commit()

        token, _, _ = create_access_token(user.id, user.role.value)
        return self._build_login_response(user, token)

    # -- 登录 --

    async def login(self, username: str, password: str) -> LoginResponse:
        user = await self.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用，请联系管理员",
            )

        token, _, _ = create_access_token(user.id, user.role.value)
        return self._build_login_response(user, token)

    # -- 登出 --

    async def logout(self, token_str: str) -> None:
        payload = decode_access_token(token_str)
        if payload:
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                remaining = exp - payload.get("iat", exp)
                if remaining > 0:
                    await blacklist_token(jti, int(remaining))

    # -- 修改密码 --

    async def change_password(self, user_id: int, old_pwd: str, new_pwd: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not verify_password(old_pwd, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码错误",
            )
        user.password_hash = hash_password(new_pwd)
        await self.db.commit()

    # -- 获取当前用户 --

    async def get_current_user_from_token(self, token_str: str) -> User | None:
        payload = decode_access_token(token_str)
        if payload is None:
            return None
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = await self.user_repo.get_by_id(int(user_id))
        if not user or not user.is_active:
            return None
        return user

    # -- 初始超管 --

    async def ensure_superadmin(self, username: str, password: str) -> None:
        count = await self.user_repo.count_users()
        if count > 0:
            return
        pwd_hash = hash_password(password)
        await self.user_repo.create(
            username=username,
            password_hash=pwd_hash,
            role=UserRole.SUPER_ADMIN,
        )
        await self.db.commit()

    # -- 生成激活码 --

    async def generate_codes(
        self, count: int, note: str | None = None, creator_id: int | None = None
    ) -> list[ActivationCode]:
        codes = []
        for _ in range(count):
            raw = generate_code()
            ac = await self.code_repo.create(raw, note, creator_id)
            codes.append(ac)
        await self.db.commit()
        return codes

    async def list_codes(
        self,
        status_filter: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ActivationCode], int]:
        return await self.code_repo.list_all(status_filter, search, offset, limit)

    async def toggle_code_status(self, code_id: int) -> ActivationCode | None:
        ac = await self.code_repo.toggle_status(code_id)
        if ac:
            await self.db.commit()
        return ac

    async def update_code_note(self, code_id: int, note: str | None) -> ActivationCode | None:
        ac = await self.code_repo.update_note(code_id, note)
        if ac:
            await self.db.commit()
        return ac
