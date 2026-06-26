from sqlalchemy import select
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
