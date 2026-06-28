
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def count_users(self) -> int:
        result = await self.db.execute(select(User))
        return len(result.scalars().all())

    async def create(
        self,
        username: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        activation_code_id: int | None = None,
    ) -> User:
        user = User(
            username=username,
            password_hash=password_hash,
            role=role,
            activation_code_id=activation_code_id,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_password(self, user_id: int, new_hash: str) -> None:
        user = await self.get_by_id(user_id)
        if user:
            user.password_hash = new_hash
            await self.db.flush()

    async def list_admins(
        self,
        role_filter: str | None = None,
        active_filter: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        query = select(User).where(
            or_(User.role == UserRole.ADMIN, User.role == UserRole.SUPER_ADMIN)
        )

        if role_filter:
            query = query.where(User.role == role_filter)

        if active_filter is not None:
            query = query.where(User.is_active == active_filter)

        if search:
            query = query.where(User.username.ilike(f"%{search}%"))

        # 计数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页
        query = query.order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total

    async def update_role(self, user_id: int, new_role: UserRole) -> User | None:
        user = await self.get_by_id(user_id)
        if user:
            user.role = new_role
            await self.db.flush()
        return user

    async def toggle_active(self, user_id: int) -> User | None:
        user = await self.get_by_id(user_id)
        if user:
            user.is_active = not user.is_active
            await self.db.flush()
        return user

    async def delete_user(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            await self.db.delete(user)
            await self.db.flush()
            return True
        return False

