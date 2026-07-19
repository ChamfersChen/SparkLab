"""模板业务逻辑层。"""

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.tag import Tag
from sparklab.models.template import Template
from sparklab.repositories.template_repository import TemplateRepository, TemplateRunRepository

_VAR_REGEX = re.compile(r"\{\{(.*?)\}\}")


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TemplateRepository(db)

    @staticmethod
    def _extract_variables(content: str) -> list[str]:
        """从 content 中提取所有 {{变量名}}。"""
        return list(dict.fromkeys(m.strip() for m in _VAR_REGEX.findall(content or "")))

    @staticmethod
    def _validate_variable_hints_coverage(content: str, variable_hints: dict | None) -> None:
        """校验 content 中出现的 {{变量}} 都被 variable_hints 覆盖。

        当 variable_hints 为 None 时视为「按需配置」,不强制覆盖;
        当 variable_hints 为 dict(允许空 dict)时,content 里出现的每个变量都必须有 hint。
        """
        if variable_hints is None:
            return
        used = set(TemplateService._extract_variables(content))
        covered = set(variable_hints.keys())
        missing = sorted(used - covered)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下变量在 content 中出现但未在 variable_hints 中配置：{', '.join(missing)}",
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
        include_private: bool = False,
    ) -> tuple[list, int]:
        """查询模板列表。

        Args:
            include_private: 是否包含私有模板。管理员查看时设为 True。
        """
        return await self.repo.list_all(
            search=search,
            tag_id_groups=tag_id_groups,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by,
            include_private=include_private,
        )

    async def list_user_templates(
        self,
        user_id: int,
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "newest",
    ) -> tuple[list, int]:
        """查询用户自己的模板列表（包含私有和公开的）。"""
        return await self.repo.list_by_user(
            user_id=user_id,
            search=search,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by,
        )

    async def get_template(self, template_id: int) -> Template | None:
        return await self.repo.get_by_id(template_id)

    async def get_template_for_user(self, template_id: int, user_id: int | None) -> Template | None:
        """按作者可见性获取模板。

        - published 且非私有: 任何登录用户可见
        - 私有模板: 仅 creator 可见
        - draft / archived: 仅 creator 可见
        - 不存在或不满足可见性 → 返回 None(路由层转 404)
        """
        template = await self.get_template(template_id)
        if template is None:
            return None
        status_value = template.status.value if hasattr(template.status, "value") else template.status
        # 私有模板：仅创建者可见
        if template.is_private:
            if user_id is not None and template.creator_id == user_id:
                return template
            return None
        # 公开模板：published 状态任何用户可见，其他状态仅创建者可见
        if status_value == "published":
            return template
        if user_id is not None and template.creator_id == user_id:
            return template
        return None

    async def create_template(
        self,
        title: str,
        description: str,
        content: str = "",
        creator_id: int | None = None,
        variable_hints: dict | None = None,
        tag_ids: list[int] | None = None,
        status: str = "draft",
        is_private: bool = False,
    ):
        await self._validate_tag_ids(tag_ids)
        self._validate_variable_hints_coverage(content, variable_hints)
        template = await self.repo.create(
            title=title,
            description=description,
            content=content,
            variable_hints=variable_hints,
            status=status,
            creator_id=creator_id,
            tag_ids=tag_ids,
            is_private=is_private,
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
        content = kwargs.get("content")
        if variable_hints is not None and content is not None:
            self._validate_variable_hints_coverage(content, variable_hints)
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

        约束: 已发布（published）模板不允许直接删除，需先在管理列表中下线为 archived。
        （Playbook 不再引用 Template, 故无需跨模块引用检查。）
        """
        template = await self.repo.get_by_id(template_id)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在",
            )
        status_value = template.status.value if hasattr(template.status, "value") else template.status
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

    async def extract_variables(self, content: str) -> dict:
        variables = self._extract_variables(content)
        return {"variables": variables}


class TemplateRunService:
    """模板使用记录业务逻辑层."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TemplateRunRepository(db)

    async def create_run(
        self,
        *,
        user,
        template_id: int,
        title: str | None,
        generated_prompt: str,
        form_values: dict,
        ai_result: str | None = None,
    ):
        from datetime import datetime as _dt

        template = await self.db.get(Template, template_id)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模板不存在",
            )
        status_value = template.status.value if hasattr(template.status, "value") else template.status
        if status_value != "published":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能保存已发布模板的使用记录",
            )

        final_title = (title or "").strip() or f"{template.title} · {_dt.now().strftime('%Y-%m-%d %H:%M')}"

        run = await self.repo.create_with_prompt(
            user_id=user.id,
            template_id=template_id,
            title=final_title,
            generated_prompt=generated_prompt,
            form_values=form_values,
            ai_result=ai_result,
        )
        await self.db.commit()
        return await self.repo.get_by_id_for_user(run.id, user.id)

    async def list_user_runs(
        self,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[dict], int]:
        runs, total = await self.repo.list_by_user(user_id, offset=offset, limit=limit)
        return [
            {
                "id": r.id,
                "template_id": r.template_id,
                "template_title": r.template.title if r.template else "",
                "title": r.title,
                "created_at": r.created_at,
                "has_prompt": bool((r.generated_prompt or "").strip()),
                "has_result": bool((r.ai_result or "").strip()),
            }
            for r in runs
        ], total

    async def get_user_run(self, user_id: int, run_id: int):
        return await self.repo.get_by_id_for_user(run_id, user_id)

    async def delete_user_run(self, user_id: int, run_id: int) -> bool:
        ok = await self.repo.delete(run_id, user_id)
        if ok:
            await self.db.commit()
        return ok
