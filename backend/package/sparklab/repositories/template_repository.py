"""模板数据访问层。"""

import json

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sparklab.models.template import Template, TemplateStatus, TemplateTag


class TemplateRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, template_id: int) -> Template | None:
        result = await self.db.execute(
            select(Template)
            .where(Template.id == template_id)
            .options(selectinload(Template.tags))
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        *,
        search: str | None = None,
        tag_id_groups: list[list[int]] | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
        sort_by: str = "use_count",
    ) -> tuple[list[Template], int]:
        query = select(Template).options(selectinload(Template.tags))
        count_query = select(func.count(Template.id))

        # 搜索
        if search:
            pattern = f"%{search}%"
            query = query.where(
                Template.title.ilike(pattern) | Template.description.ilike(pattern)
            )
            count_query = count_query.where(
                Template.title.ilike(pattern) | Template.description.ilike(pattern)
            )

        # 状态筛选
        if status:
            query = query.where(Template.status == status)
            count_query = count_query.where(Template.status == status)

        # 标签筛选：组间 AND、组内 OR
        if tag_id_groups:
            for group in tag_id_groups:
                if not group:
                    continue
                exists_clause = (
                    select(TemplateTag.template_id)
                    .where(
                        TemplateTag.template_id == Template.id,
                        TemplateTag.tag_id.in_(group),
                    )
                    .exists()
                )
                query = query.where(exists_clause)
                count_query = count_query.where(exists_clause)

        # 排序
        if sort_by == "newest":
            query = query.order_by(Template.created_at.desc())
        else:
            query = query.order_by(Template.use_count.desc(), Template.created_at.desc())

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def create(
        self,
        title: str,
        description: str,
        content: str,
        variable_hints: dict | None = None,
        status: str = "draft",
        creator_id: int | None = None,
        tag_ids: list[int] | None = None,
    ) -> Template:
        template = Template(
            title=title,
            description=description,
            content=content,
            variable_hints=json.dumps(variable_hints, ensure_ascii=False) if variable_hints else None,
            status=TemplateStatus(status),
            creator_id=creator_id,
        )
        self.db.add(template)
        await self.db.flush()

        if tag_ids:
            for tid in tag_ids:
                self.db.add(TemplateTag(template_id=template.id, tag_id=tid))
            await self.db.flush()

        return template

    async def update(
        self,
        template_id: int,
        **kwargs,
    ) -> Template | None:
        template = await self.db.get(Template, template_id)
        if not template:
            return None

        # 处理特殊字段
        tag_ids = kwargs.pop("tag_ids", None)
        variable_hints = kwargs.pop("variable_hints", None)
        status = kwargs.pop("status", None)

        for key, value in kwargs.items():
            if value is not None:
                setattr(template, key, value)

        if variable_hints is not None:
            template.variable_hints = json.dumps(variable_hints, ensure_ascii=False)
        if status is not None:
            template.status = TemplateStatus(status)

        await self.db.flush()

        if tag_ids is not None:
            await self.db.execute(
                TemplateTag.__table__.delete().where(TemplateTag.template_id == template_id)
            )
            for tid in tag_ids:
                self.db.add(TemplateTag(template_id=template_id, tag_id=tid))
            await self.db.flush()

        return template

    async def update_status(self, template_id: int, status: str) -> Template | None:
        template = await self.db.get(Template, template_id)
        if not template:
            return None
        template.status = TemplateStatus(status)
        await self.db.flush()
        return template

    async def increment_use_count(self, template_id: int) -> None:
        await self.db.execute(
            update(Template)
            .where(Template.id == template_id)
            .values(use_count=Template.use_count + 1)
        )
        await self.db.flush()

    async def delete(self, template_id: int) -> bool:
        template = await self.db.get(Template, template_id)
        if not template:
            return False
        template.status = TemplateStatus.ARCHIVED
        await self.db.flush()
        return True

    async def hard_delete(self, template_id: int) -> bool:
        template = await self.db.get(Template, template_id)
        if not template:
            return False
        await self.db.delete(template)
        await self.db.flush()
        return True
