"""模板业务逻辑层。"""

import json
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.tag import Tag
from sparklab.models.template import Template
from sparklab.repositories.template_repository import TemplateRepository


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TemplateRepository(db)

    @staticmethod
    def _extract_variables(input_text: str) -> list[str]:
        """从 Input 段中提取所有 {{变量名}}。"""
        return list(dict.fromkeys(re.findall(r"\{\{(.*?)\}\}", input_text)))

    async def _validate_tag_ids(self, tag_ids: list[int] | None) -> None:
        """校验 tag_ids 全部存在；空/None 直接通过。"""
        if not tag_ids:
            return
        unique_ids = list(dict.fromkeys(tag_ids))
        result = await self.db.execute(select(Tag.id).where(Tag.id.in_(unique_ids)))
        existing = {row[0] for row in result.all()}
        missing = [tid for tid in unique_ids if tid not in existing]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下标签不存在：{', '.join(map(str, missing))}",
            )

    async def list_templates(
        self,
        search: str | None = None,
        tag_ids: list[int] | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "use_count",
    ) -> tuple[list, int]:
        return await self.repo.list_all(
            search=search,
            tag_ids=tag_ids,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by,
        )

    async def get_template(self, template_id: int) -> Template | None:
        """获取模板，同时解析 variable_hints JSON 为 dict。"""
        template = await self.repo.get_by_id(template_id)
        if template and isinstance(template.variable_hints, str):
            try:
                template.variable_hints = json.loads(template.variable_hints)
            except (json.JSONDecodeError, TypeError):
                template.variable_hints = None
        return template

    async def create_template(
        self,
        title: str,
        description: str,
        role: str,
        goal: str,
        input: str,
        output: str,
        example: str,
        creator_id: int | None = None,
        variable_hints: dict | None = None,
        tag_ids: list[int] | None = None,
        status: str = "draft",
    ):
        await self._validate_tag_ids(tag_ids)
        template = await self.repo.create(
            title=title,
            description=description,
            role=role,
            goal=goal,
            input=input,
            output=output,
            example=example,
            variable_hints=variable_hints,
            status=status,
            creator_id=creator_id,
            tag_ids=tag_ids,
        )
        await self.db.commit()
        return await self.get_template(template.id)

    async def update_template(
        self,
        template_id: int,
        **kwargs,
    ):
        tag_ids = kwargs.get("tag_ids")
        if tag_ids is not None:
            await self._validate_tag_ids(tag_ids)
        template = await self.repo.update(template_id, **kwargs)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在",
            )
        await self.db.commit()
        return await self.get_template(template_id)

    async def change_status(self, template_id: int, new_status: str):
        valid_statuses = {"draft", "published", "archived"}
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值，可选：{', '.join(sorted(valid_statuses))}",
            )
        template = await self.repo.update_status(template_id, new_status)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在",
            )
        await self.db.commit()
        return await self.get_template(template_id)

    async def delete_template(self, template_id: int) -> None:
        deleted = await self.repo.delete(template_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在",
            )
        await self.db.commit()

    async def increment_use_count(self, template_id: int) -> None:
        await self.repo.increment_use_count(template_id)
        await self.db.commit()

    async def extract_variables(self, input_text: str) -> dict:
        """解析 Input 段变量并返回变量清单（无持久化）。"""
        variables = self._extract_variables(input_text)
        return {"variables": variables}
