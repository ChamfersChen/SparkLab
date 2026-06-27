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

    @staticmethod
    def _validate_variable_hints_coverage(
        input_text: str, variable_hints: dict | None
    ) -> None:
        """校验 Input 段出现的 {{变量}} 都被 variable_hints 覆盖。

        当 variable_hints 为 None 时视为「按需配置」,不强制覆盖;
        当 variable_hints 为 dict(允许空 dict)时,Input 段里出现的每个变量都必须有 hint。
        """
        if variable_hints is None:
            return
        used = set(TemplateService._extract_variables(input_text))
        covered = set(variable_hints.keys())
        missing = sorted(used - covered)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下变量在 Input 段出现但未在 variable_hints 中配置：{', '.join(missing)}",
            )

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
        tag_id_groups: list[list[int]] | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "use_count",
    ) -> tuple[list, int]:
        return await self.repo.list_all(
            search=search,
            tag_id_groups=tag_id_groups,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by,
        )

    async def get_template(self, template_id: int) -> Template | None:
        """获取模板。

        不做作者可见性过滤，调用方需自行决定是否使用 get_template_for_user。
        不在 instance 上修改 variable_hints(避免污染 SQLAlchemy session 的 dirty 状态)；
        hints 的 JSON 解析由 Pydantic 响应模型的 parse_hints 字段 validator 负责。
        """
        return await self.repo.get_by_id(template_id)

    async def get_template_for_user(
        self, template_id: int, user_id: int | None
    ) -> Template | None:
        """按作者可见性获取模板。

        - published: 任何登录用户可见
        - draft / archived: 仅 creator 可见
        - 未登录用户仅能看 published
        - 不存在或不满足可见性 → 返回 None(路由层转 404)
        """
        template = await self.get_template(template_id)
        if template is None:
            return None
        status_value = (
            template.status.value
            if hasattr(template.status, "value")
            else template.status
        )
        if status_value == "published":
            return template
        if user_id is not None and template.creator_id == user_id:
            return template
        return None

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
        self._validate_variable_hints_coverage(input, variable_hints)
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
        variable_hints = kwargs.get("variable_hints")
        input_text = kwargs.get("input")
        if variable_hints is not None and input_text is not None:
            self._validate_variable_hints_coverage(input_text, variable_hints)
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

    async def hard_delete_template(self, template_id: int) -> None:
        """物理删除模板（仅超管使用）。

        从 DB 中删除该条记录；template_tags 关联靠 CASCADE 自动清理。
        不可恢复，请确认后调用。

        约束：已发布（published）模板不允许直接删除，需先在管理列表中下线为 archived。
        """
        template = await self.repo.get_by_id(template_id)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在",
            )
        status_value = (
            template.status.value
            if hasattr(template.status, "value")
            else template.status
        )
        if status_value == "published":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="已发布的模板不能删除,请先在列表中下线为「已归档」后再操作",
            )
        deleted = await self.repo.hard_delete(template_id)
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
