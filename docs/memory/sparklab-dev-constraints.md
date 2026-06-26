---
name: sparklab-dev-constraints
description: SparkLab 必须遵守的架构不变量与开发流程约束（违反这些等于偏离设计）
metadata: 
  node_type: memory
  type: project
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

**架构不变量（不可违反）**：

1. **路由薄、领域厚**：HTTP 路由 (`backend/server/routers`) 只做请求解析 / 认证 / 响应装配；业务逻辑在 `backend/package/sparklab/services`；DB 查询走 `backend/package/sparklab/repositories`。路由不许绕过 repository 直接操作 SQLAlchemy 模型。
2. **认证**：JWT Token + `Authorization: Bearer <token>` Header（前端 localStorage 存储）；黑名单存 Redis；后端依赖注入 `get_current_user` / `get_current_admin` / `get_current_super_admin` 做权限边界。**与 Yuxi 一致**（2026-06-25 决策，见 [[sparklab-auth-bearer-header]]）。
3. **软删除**：模板、工作流删除只更新 `status = archived`，不物理删。
4. **工作流步骤状态在前端管理**（未开始/当前/已完成），**不持久化到后端**。
5. **变量语法**：模板用 `{{变量名}}` 定义，前端正则提取并自动生成表单；`variable_hints` 是 JSON `{"变量名": "提示文案"}`。
6. **前端 API 集中**：所有后端调用必须封装在 `web/src/apis`，组件不许散落拼 URL。
7. **样式 token 化**：颜色一律走 `web/src/assets/css/base.css` CSS 变量（主色 `--main-color: #3B82F6`），不能硬编码。
8. **使用次数计数规则**：模板在点击「生成提示词」时 `use_count +1`；工作流在用户完成至少一个 Step 时 `use_count +1`。
9. **不允许过度防御/回退掩盖设计缺陷**：错误要及时暴露和修复，不要用冗余兜底吞掉。

**开发工作流**：
- 后端开发/调试在 Docker 容器内：`docker ps` 检查服务 → `docker logs sparklab-api-dev --tail 100` 看日志；api-dev 热重载，改完后端代码不要重启容器
- 前端走本机 `pnpm dev`（端口 5173），Vite 自带热重载；`docker-compose.yml` 中 `web-dev` 服务已注释保留
- 测试目录：`backend/test/{unit, integration, e2e}`，提交前必须跑通
- 改动较大时，在 `docs/` 下建带日期的需求文档（目标 + checklist）
- 提交：Conventional Commits + **中文** 提交信息

**代码风格**：
- Python 3.12+ pythonic，避免旧语法
- 不为简单线性逻辑拆细碎 helper；拆函数必须服务于复用 / 隔离副作用 / 降低认知负担
- 前端组件优先复用 Ant Design Vue 和项目现有模式
- 图标 `lucide-vue-next`，尺寸 16/18/20px
- 卡片样式：`background: var(--gray-0); border: 1px solid var(--gray-150); border-radius: 8px;`
- hover **不**位移/放大/旋转；普通卡片**不**加阴影

详见 [[sparklab-project-overview]] 和项目根 `AGENTS.md` / `docs/design.md`。
