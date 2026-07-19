"""工作流 (Playbook) 业务逻辑层。

约定:
  - 路由层 (playbook_router / playbook_admin_router) 保持薄, 只调 service
  - 业务校验 (tag_ids / 变量覆盖) 在 service 层统一处理

Prompt 模型:
  - Template/Playbook/PlaybookStep 都只剩一个 `content` 字段 (Markdown + {{var}})
  - PlaybookStep 额外支持特殊占位符 {{prev_output}} — 由用户在运行期把上一步 AI 平台
    的返回结果粘回,后端按 step_order 顺序串起来。
"""

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sparklab.models.playbook import Playbook
from sparklab.models.tag import Tag
from sparklab.repositories.playbook_repository import PlaybookRepository
from sparklab.schemas.playbook import (
    PlaybookRunResponse,
    PlaybookRunStep,
)

_VAR_REGEX = re.compile(r"\{\{(.*?)\}\}")


def fill_step_prompt(content: str, form_values: dict | None, prev_output: str | None) -> str:
    """纯函数: 把 content 里的 {{prev_output}} + {{var}} 按顺序替换.

    - prev_output: 优先替换 (若 content 含 {{prev_output}} 且 prev_output 不为 None)
    - form_values: 其余 {{var}} 替换
    """
    text = content or ""
    if prev_output and "{{prev_output}}" in text:
        text = text.replace("{{prev_output}}", prev_output)
    fv = form_values or {}

    def repl(m):
        key = m.group(1).strip()
        if key == "prev_output":
            return prev_output or m.group(0)
        val = fv.get(key)
        return val.strip() if val is not None else m.group(0)

    return _VAR_REGEX.sub(repl, text)


class PlaybookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PlaybookRepository(db)

    # ------------------------------------------------------------------
    # private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_variables(text: str) -> list[str]:
        """提取 content 中所有 {{变量名}}，但排除特殊占位符 {{prev_output}}。"""
        out: list[str] = []
        seen: set[str] = set()
        for m in _VAR_REGEX.finditer(text or ""):
            key = m.group(1).strip()
            if key == "prev_output":
                continue
            if key not in seen:
                seen.add(key)
                out.append(key)
        return out

    @staticmethod
    def _validate_variable_hints_coverage(content: str, variable_hints: dict | None) -> None:
        """校验 content 中出现的 {{变量}} 都被 variable_hints 覆盖。"""
        if variable_hints is None:
            return
        used = set(PlaybookService._extract_variables(content))
        covered = set(variable_hints.keys())
        missing = sorted(used - covered)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"以下变量在 content 中出现但未在 variable_hints 中配置：{', '.join(missing)}",
            )

    async def _validate_tag_ids(self, tag_ids: list[int] | None) -> None:
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

    def _normalize_steps(self, steps: list) -> list[dict]:
        """重排 step_order 0..N-1；空 name 用 "Step N" 兜底；不允许完全同 name+content 的重复。

        支持 dict / 对象两种 step 形态。
        """
        if not steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="工作流至少需要 1 个步骤",
            )

        def _get(s, key, default=None):
            if isinstance(s, dict):
                return s.get(key, default)
            return getattr(s, key, default)

        # 重复校验: 名字 + 内容完全相同视为重复
        seen_signatures: set[tuple[str, str]] = set()
        for s in steps:
            sig = ((_get(s, "name", "") or "").strip(), _get(s, "content", "") or "")
            if sig in seen_signatures:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="工作流中存在完全重复的步骤（name + content 都相同）",
                )
            seen_signatures.add(sig)

        normalized: list[dict] = []
        for i, s in enumerate(steps):
            name = (_get(s, "name", "") or "").strip() or f"Step {i + 1}"
            normalized.append(
                {
                    "step_order": i,
                    "name": name,
                    "description": _get(s, "description") or None,
                    "content": _get(s, "content", "") or "",
                }
            )
        return normalized

    @staticmethod
    def _fill_variables(text: str, values: dict[str, str]) -> str:
        """把 {{var}} 替换为 values[var]（trim 后的值）；缺失的 var 保留原样。"""

        def repl(m: re.Match) -> str:
            key = m.group(1).strip()
            val = values.get(key)
            return val.strip() if val is not None else m.group(0)

        return _VAR_REGEX.sub(repl, text or "")

    @staticmethod
    def _fill_with_specials(content: str, form_values: dict, prev_output: str | None) -> tuple[str, bool]:
        """先替换 {{prev_output}}（若 content 引用了 + prev_output 不为 None），再替换其余 {{var}}。

        返回 (filled_text, prev_output_injected)。
        """
        prev_injected = False
        text = content or ""
        if prev_output is not None and "{{prev_output}}" in text:
            text = text.replace("{{prev_output}}", prev_output)
            prev_injected = True
        # 之后用 form_values 替换剩余 {{var}}, 但跳过 prev_output 防止二次替换
        merged = {**form_values, "prev_output": prev_output or "{{prev_output}}"}
        text = PlaybookService._fill_variables(text, merged)
        return text, prev_injected

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def list_playbooks(
        self,
        search: str | None = None,
        tag_id_groups: list[list[int]] | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "use_count",
        include_private: bool = False,
    ) -> tuple[list, int]:
        """查询流程列表。

        Args:
            include_private: 是否包含私有流程。管理员查看时设为 True。
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

    async def list_user_playbooks(
        self,
        user_id: int,
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "newest",
    ) -> tuple[list, int]:
        """查询用户自己的流程列表（包含私有和公开的）。"""
        return await self.repo.list_by_user(
            user_id=user_id,
            search=search,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
            sort_by=sort_by,
        )

    async def get_playbook(self, playbook_id: int) -> Playbook | None:
        return await self.repo.get_by_id(playbook_id)

    async def get_playbook_for_user(self, playbook_id: int, user) -> Playbook | None:
        """可见性规则:
        - 私有流程: 仅 creator 可见
        - 公开流程 published: 任何登录用户
        - 公开流程 draft / archived: 仅 creator 或 admin / super_admin
        """
        playbook = await self.get_playbook(playbook_id)
        if playbook is None:
            return None
        status_value = playbook.status.value if hasattr(playbook.status, "value") else playbook.status
        # 私有流程：仅创建者可见
        if playbook.is_private:
            if user is not None and getattr(user, "id", None) == playbook.creator_id:
                return playbook
            return None
        # 公开流程：按状态判断
        if status_value == "published":
            return playbook
        if user is not None:
            user_role = getattr(user, "role", "user")
            if user_role in ("admin", "super_admin"):
                return playbook
            if getattr(user, "id", None) == playbook.creator_id:
                return playbook
        return None

    # ------------------------------------------------------------------
    # 写操作
    # ------------------------------------------------------------------

    async def create_playbook(
        self,
        *,
        title: str,
        description: str,
        content: str = "",
        variable_hints: dict | None,
        steps: list,
        tag_ids: list[int] | None,
        status: str,
        creator_id: int | None,
        is_private: bool = False,
    ) -> Playbook:
        await self._validate_tag_ids(tag_ids)
        self._validate_variable_hints_coverage(content, variable_hints)
        # 校验每个 step 自身的 content 变量覆盖(若该 step 设了 variable_hints,
        # Pydantic 不再接收 — 这里是 playbook 级, 不与 step content 重复校验)
        for s in steps:
            step_content = s.get("content", "") if isinstance(s, dict) else getattr(s, "content", "")
            step_vars = self._extract_variables(step_content or "")
            if step_vars:
                # step 级 content 有变量, 但无 hints 入口: 不强制覆盖, 仅记录
                pass
        normalized_steps = self._normalize_steps(steps)

        playbook = await self.repo.create(
            title=title,
            description=description,
            content=content,
            variable_hints=variable_hints,
            steps=normalized_steps,
            status=status,
            creator_id=creator_id,
            tag_ids=tag_ids,
            is_private=is_private,
        )
        await self.db.commit()
        return await self.get_playbook(playbook.id)

    async def update_playbook(self, playbook_id: int, **kwargs):
        if "tag_ids" in kwargs and kwargs["tag_ids"] is not None:
            await self._validate_tag_ids(kwargs["tag_ids"])

        variable_hints = kwargs.get("variable_hints")
        content = kwargs.get("content")
        if variable_hints is not None and content is not None:
            self._validate_variable_hints_coverage(content, variable_hints)

        if "steps" in kwargs and kwargs["steps"] is not None:
            kwargs["steps"] = self._normalize_steps(kwargs["steps"])

        playbook = await self.repo.update(playbook_id, **kwargs)
        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )
        await self.db.commit()
        return await self.get_playbook(playbook_id)

    async def change_status(self, playbook_id: int, new_status: str) -> Playbook:
        valid_statuses = {"draft", "published", "archived"}
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值，可选：{', '.join(sorted(valid_statuses))}",
            )
        playbook = await self.repo.update_status(playbook_id, new_status)
        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )
        await self.db.commit()
        return await self.get_playbook(playbook_id)

    async def delete_playbook(self, playbook_id: int) -> None:
        ok = await self.repo.delete(playbook_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )
        await self.db.commit()

    async def hard_delete_playbook(self, playbook_id: int) -> None:
        playbook = await self.repo.get_by_id(playbook_id)
        if playbook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )
        status_value = playbook.status.value if hasattr(playbook.status, "value") else playbook.status
        if status_value == "published":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="已发布的工作流不能删除,请先在列表中下线为「已归档」后再操作",
            )
        ok = await self.repo.hard_delete(playbook_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )
        await self.db.commit()

    async def increment_use_count(self, playbook_id: int) -> None:
        await self.repo.increment_use_count(playbook_id)
        await self.db.commit()

    # ------------------------------------------------------------------
    # 运行
    # ------------------------------------------------------------------

    async def run_playbook(
        self,
        playbook_id: int,
        user,
        form_values: dict[str, str],
        step_outputs: list,
    ) -> PlaybookRunResponse:
        """运行工作流: 拼接所有步骤的 prompt。

        关键: 每步渲染时, 先尝试把 {{prev_output}} 替换为该步骤的 prev_output (来自前端),
        再用该步骤的 form_values 替换其余 {{var}}。prev_output 来自上一步的 AI 平台返回结果,
        由前端按 step_order 顺序提交到 step_outputs[].prev_output。
        """
        playbook = await self.get_playbook_for_user(playbook_id, user)
        if playbook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )

        # 1) 工作流级 content
        wf_filled = self._fill_variables(playbook.content or "", form_values or {})

        # 2) step_outputs 按 step_order 建索引
        step_outputs_map: dict[int, object] = {so.step_order: so for so in (step_outputs or [])}
        valid_orders = {s.step_order for s in playbook.steps}
        for order in step_outputs_map.keys():
            if order not in valid_orders:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"step_outputs 包含未知 step_order: {order}",
                )

        # 3) 按 step_order 顺序渲染
        rendered_steps: list[PlaybookRunStep] = []
        for step in playbook.steps:
            so = step_outputs_map.get(step.step_order)
            so_form = so.form_values if so else {}
            so_prev = so.prev_output if so else None
            filled, prev_injected = self._fill_with_specials(step.content or "", so_form or {}, so_prev)
            rendered_steps.append(
                PlaybookRunStep(
                    step_order=step.step_order,
                    name=step.name,
                    filled_content=filled,
                    prev_output_injected=prev_injected,
                )
            )

        # 4) 拼最终 prompt
        step_blocks = "\n\n---\n\n".join(s.filled_content for s in rendered_steps)
        final_prompt = wf_filled + ("\n\n---\n\n" + step_blocks if step_blocks else "")

        return PlaybookRunResponse(
            playbook_id=playbook.id,
            playbook_title=playbook.title,
            final_prompt=final_prompt,
            steps=rendered_steps,
        )


# ===========================================================================
# 工作流运行记录 (个人中心 / 我的运行记录)
# ===========================================================================

from datetime import datetime as _dt

from sparklab.models.playbook import PlaybookRun  # noqa: E402
from sparklab.repositories.playbook_repository import (
    PlaybookRunRepository,  # noqa: E402
    summarize_run,  # noqa: E402
)


class PlaybookRunService:
    """个人中心「我的运行记录」的业务层.

    与 PlaybookService 平级, 但服务对象不同: 这里是"用户保存的运行结果"而非
    "工作流定义本身". 故独立类, 共享 session 注入风格.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PlaybookRunRepository(db)

    async def create_run(
        self,
        *,
        user,
        playbook_id: int,
        title: str | None,
        steps_data: list[dict],
        final_result: str | None = None,
    ) -> PlaybookRun:
        """保存一次工作流运行结果.

        校验:
          - user 已登录 (路由层 get_required_user 保证)
          - playbook 存在且 status=published
          - steps_data 至少 1 项
          - step_order 与 playbook 当前步骤一致
          - 至少粘回 1 个 step 的 AI 结果 OR 在右栏填了 final_result (v4: 可只保存最终结果)
        """
        playbook = await self.db.get(Playbook, playbook_id)
        if playbook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="工作流不存在",
            )
        status_value = playbook.status.value if hasattr(playbook.status, "value") else playbook.status
        if status_value != "published":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能保存已发布工作流的运行结果",
            )

        if not steps_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要 1 个步骤",
            )

        valid_orders = {s.step_order for s in playbook.steps}
        for s in steps_data:
            if int(s["step_order"]) not in valid_orders:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"steps 含未知 step_order: {s.get('step_order')}",
                )

        # v4: 至少粘回 1 个 step OR 填了 final_result
        has_step_output = any((s.get("user_output") or "").strip() for s in steps_data)
        has_final = bool((final_result or "").strip())
        if not has_step_output and not has_final:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要粘回 1 个步骤的 AI 结果,或在右栏填写最终结果",
            )

        # v4: server 现算每 step 的 filled_prompt 快照
        # 顺序: 按 step_order 升序; prev_output = 前一步的 user_output
        sorted_steps = sorted(steps_data, key=lambda s: int(s["step_order"]))
        # 通过 playbook.steps 关系读取 (已 selectinload, 见 Playbook 定义)
        step_index_map = {int(p.step_order): p for p in playbook.steps}
        filled_prompts: list[str | None] = []
        prev_user_output: str | None = None
        for s in sorted_steps:
            order = int(s["step_order"])
            step_def = step_index_map.get(order)
            content = step_def.content if step_def else ""
            fv = s.get("form_values") or {}
            # 当前 step 的 prev_output = 上一步的 user_output (可能 None)
            filled = fill_step_prompt(content, fv, prev_user_output)
            filled_prompts.append(filled)
            # 更新 prev: 只有非空 user_output 才作为下一步的 prev_output
            cur_out = (s.get("user_output") or "").strip() or None
            prev_user_output = cur_out

        # 默认标题: 留空时用 playbook.title + 时间戳
        final_title = (title or "").strip() or f"{playbook.title} · {_dt.now().strftime('%Y-%m-%d %H:%M')}"

        run = await self.repo.create_with_steps(
            user_id=user.id,
            playbook_id=playbook_id,
            title=final_title,
            steps_data=steps_data,
            final_result=final_result,
            filled_prompts=filled_prompts,
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
        return [summarize_run(r) for r in runs], total

    async def get_user_run(self, user_id: int, run_id: int) -> PlaybookRun | None:
        return await self.repo.get_by_id_for_user(run_id, user_id)

    async def delete_user_run(self, user_id: int, run_id: int) -> bool:
        ok = await self.repo.delete(run_id, user_id)
        if ok:
            await self.db.commit()
        return ok
