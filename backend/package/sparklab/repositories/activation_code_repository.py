from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from sparklab.models.activation_code import ActivationCode, ActivationCodeStatus
from sparklab.models.user import User


class ActivationCodeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, code_id: int) -> ActivationCode | None:
        return await self.db.get(ActivationCode, code_id)

    async def get_by_code(self, code: str) -> ActivationCode | None:
        result = await self.db.execute(select(ActivationCode).where(ActivationCode.code == code))
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status_filter: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ActivationCode], int]:
        query = (
            select(ActivationCode).options(joinedload(ActivationCode.user)).options(joinedload(ActivationCode.creator))
        )
        count_query = select(ActivationCode)

        if status_filter:
            query = query.where(ActivationCode.status == status_filter)
            count_query = count_query.where(ActivationCode.status == status_filter)
        if search:
            like = f"%{search}%"
            query = query.where(
                ActivationCode.code.ilike(like)
                | ActivationCode.note.ilike(like)
                | ActivationCode.user.has(User.username.ilike(like))
                | ActivationCode.creator.has(User.username.ilike(like))
            )
            count_query = count_query.where(
                ActivationCode.code.ilike(like)
                | ActivationCode.note.ilike(like)
                | ActivationCode.user.has(User.username.ilike(like))
                | ActivationCode.creator.has(User.username.ilike(like))
            )

        total_result = await self.db.execute(count_query)
        total = len(total_result.scalars().all())

        query = query.order_by(ActivationCode.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.unique().scalars().all())
        return items, total

    async def create(self, code: str, note: str | None = None, creator_id: int | None = None) -> ActivationCode:
        ac = ActivationCode(code=code, note=note, creator_id=creator_id)
        self.db.add(ac)
        await self.db.flush()
        return ac

    async def update_note(self, code_id: int, note: str | None) -> ActivationCode | None:
        ac = await self.db.get(ActivationCode, code_id)
        if ac:
            ac.note = note
            await self.db.flush()
        return ac

    async def mark_used(self, code_id: int, user_id: int) -> None:
        ac = await self.db.get(ActivationCode, code_id)
        if ac:
            ac.status = ActivationCodeStatus.USED
            ac.user_id = user_id
            ac.used_at = datetime.now(UTC)
            await self.db.flush()

    async def toggle_status(self, code_id: int) -> ActivationCode | None:
        ac = await self.db.get(ActivationCode, code_id)
        if ac and ac.status != ActivationCodeStatus.USED:
            ac.status = (
                ActivationCodeStatus.DISABLED
                if ac.status == ActivationCodeStatus.UNUSED
                else ActivationCodeStatus.UNUSED
            )
            await self.db.flush()
        return ac
