# SparkLab AGENTS.md

# 项目目录结构 (Project Overview)

SparkLab 是一个 AI 内容运营平台，为内容创作者提供提示词模板和工作流 Playbook 的管理与使用功能。基于 Vue.js + FastAPI + Postgres + Redis 架构构建，通过 Docker Compose 进行管理，支持热重载开发。

架构代码地图见 [ARCHITECTURE.md](ARCHITECTURE.md)。修改不熟悉的模块前，先阅读其中的后端、前端、运行链路和架构不变量说明，再用符号搜索定位具体实现；该文档只维护相对稳定的系统边界，不替代细节文档或源码注释。

产品设计文档见 [SparkLab-产品设计文档.md](docs/SparkLab-产品设计文档.md)，包含完整的需求说明、页面定义、API 接口清单和数据模型定义。

界面设计规范见 [design.md](docs/design.md)，包含颜色 token、组件样式、布局规范和 Agent Prompt Guide。

## 开发准则

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## 开发与调试工作流 (Development & Debugging Workflow)

本项目完全通过 Docker Compose 进行管理。所有开发和调试都应在运行的容器环境中进行。使用 `docker compose up -d` 命令进行构建和启动。

**核心原则**:

1. 由于 api-dev 服务配置了热重载 (hot-reloading)，本地修改后端代码后无需重启容器，服务会自动更新。前端走本机 `pnpm dev`（端口 5173），Vite 自带热重载。应该先检查项目是否已经在后台启动（`docker ps`），查看后端日志（`docker logs sparklab-api-dev --tail 100`），具体可阅读 [docker-compose.yml](docker-compose.yml)。
2. 开发完成之后必须进行 检查 -> 测试 -> Lint，以及端到端测试，测试脚本不完善时应完善脚本。
3. 测试规范务必遵守项目中的测试规范，测试脚本务必放在 backend/test 目录下，并且在提交前确保测试通过。
4. 非常重要！千万不要使用过度的防御/回退机制来掩盖设计上的缺陷，良好的软件应该在预设的条件下运行，其余情况均应该及时发现问题/错误并修复，而不是通过增加冗余代码来掩盖问题。

### 需求沟通规范

在沟通需求的时候，当需求不明确的时候，需要主动挖掘需求细节，对齐需求的验收标准，明确需求的优先级和范围，避免模糊需求导致的过度设计和不必要的工作。

- 需求/修改 明确之后，如果改动较大，则需要在 docs/ 目录下创建一个包含日期的文档，记录需求的细节和验收标准
- 该需求文档中，还应该包括本次任务的目标以及 checklist（简要）

### 前端开发规范

- 使用 pnpm 管理
- API 接口规范：所有的 API 接口都应该定义在 web/src/apis 下面，复用 base.js 的请求、鉴权和错误处理
- Icon 应该优先从 lucide-vue-next（推荐，注意尺寸为 16px/18px/20px）
- 样式使用 LESS，非特殊情况必须使用 [base.css](web/src/assets/css/base.css) 中的颜色变量
- UI 设计规范详见 [design.md](docs/design.md)
- 前端 API 调用应集中在 `web/src/apis`，组件不要散落拼接后端 URL
- 工作流步骤状态由前端管理，不持久化到后端
- 提示词变量解析使用 `{{变量名}}` 语法，自动生成表单输入框

**组件开发规范**:
- 页面级组件放在 `web/src/views`
- 可复用组件放在 `web/src/components`
- 可组合逻辑放在 `web/src/composables`
- 优先复用 Ant Design Vue 组件和项目现有组件模式

**布局规范**:
- 左侧固定导航（220px）+ 右侧自适应内容区
- 卡片样式：`background: var(--gray-0); border: 1px solid var(--gray-150); border-radius: 8px;`
- 状态标签：浅背景 + 深文字，圆角 999px，文字 12px

### 后端开发规范

```bash
# 代码检查和格式化
make format        # 格式化代码
```

注意：
- Python 代码要符合 pythonic 风格
- 尽量使用较新的语法，避免使用旧版本的语法（版本兼容到 3.12+）
- 更新 changelog 文档记录本次修改，多个类似的功能更新已经补充在一起
- 开发完成后务必在 docker 中进行测试，可以读取 .env 获取管理员账户和密码
- 不允许把代码写得稀碎：不要为简单线性逻辑拆出一堆细碎 helper；优先写成职责清晰、结构完整、可一眼读懂的实现。
- 拆函数必须服务于明确的复用、隔离副作用或降低认知负担；如果拆分后调用链更绕、上下文更分散，就应合并回更直接的实现。

**架构边界**:
- HTTP 路由层应保持薄；领域流程放在 `sparklab.services`，持久化查询放在 `sparklab.repositories`
- 不要让路由绕过 repository 直接操作模型
- 认证使用 JWT Token + `Authorization: Bearer` Header；前端 localStorage 存储；登出后 Token `jti` 进入 Redis 黑名单直到自然过期
- 模板和工作流使用软删除策略，只更新 `status` 字段，不物理删除

**数据库规范**:
- SQLAlchemy 模型定义在 `backend/package/sparklab/models`
- Pydantic 数据结构定义在 `backend/package/sparklab/schemas`
- 数据库迁移使用 Alembic

**权限规范**:
- 普通用户只能浏览和使用，不能发布或评论
- 管理员可发布/编辑/下线模板、工作流、资讯和标签
- 超级管理员额外管理激活码、管理员账号和 AI 平台配置
- 后端路由依赖注入 `get_current_user` 获取当前用户，`get_current_admin` 确保管理员权限

**其他**:

- 如果需要新建说明文档（仅开发者可见，非必要不创建），则保存在 `docs/` 文件夹下面
- 代码更新后要检查文档部分是否有需要更新的地方

## 提交规范

1. 参考 [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) 规范编写提交信息。
2. 使用中文提交信息，标题简洁明了，描述具体改动内容和原因。
3. 创建 PR 必须参考 contributing 文档以及 PR 模板，并在提交前完成其中的检查项。

## Agent Prompt Guide

AI agent 修改或生成 SparkLab 代码时，优先按这一节执行。

### Quick Reference

- **产品定位**：管理员发布模板/工作流/资讯 → 付费用户激活使用 → 按工作流步骤生成提示词 → 复制到第三方 AI 平台
- **核心体验**：工作流 Playbook（顺序排列，变量不传递）
- **认证方式**：激活码验证 + JWT Token + `Authorization: Bearer` Header（localStorage 存储）
- **删除策略**：软删除（status: archived）
- **标签体系**：三维标签（平台/内容类型/行业场景），管理员动态配置

### 前端实现检查清单

- 使用 `web/src/apis` 中的 API 方法，不直接拼接 URL
- 使用 `base.css` 中的 CSS 变量，没有硬编码色值
- 浅色和暗色模式都检查过
- hover、focus、disabled、loading、empty、error 状态符合场景
- 图标来自 `lucide-vue-next`，尺寸为 16px/18px/20px
- 工作流步骤状态清晰可辨（未开始/当前/已完成）
- 左侧导航和内容区布局符合 Dashboard 规范

### 后端实现检查清单

- 路由层保持薄，领域逻辑放在 services
- 使用 repository 封装数据库查询，不直接在路由操作模型
- 认证使用 JWT Token + `Authorization: Bearer` Header
- 权限检查使用依赖注入（`get_current_user` / `get_current_admin`）
- 模板和工作流使用软删除
- 变量解析使用 `{{变量名}}` 语法
- API 响应格式统一，包含错误处理
- 测试覆盖核心业务逻辑

### 示例 Prompt

实现模板列表页：

```text
实现 SparkLab 的模板列表页：
1. 使用 Vue 3 组件，放在 web/src/views/templates/
2. 调用 web/src/apis/template.js 中的 listTemplates 方法
3. 使用 Ant Design Vue 的 Card 和 Tag 组件
4. 三维标签筛选（平台/内容类型/行业场景）
5. 搜索功能
6. 卡片样式：background: var(--gray-0); border: 1px solid var(--gray-150); border-radius: 8px;
7. 状态标签：已发布使用 --color-success-50 背景和 --color-success-700 文字
8. hover 只改变背景，不使用 transform
```

实现工作流运行页：

```text
实现 SparkLab 的工作流运行页：
1. 使用 Vue 3 组件，放在 web/src/views/playbooks/
2. 调用 web/src/apis/playbook.js 中的 getPlaybook 方法
3. 显示工作流标题、描述和步骤列表
4. 步骤状态：未开始（灰色）、当前步骤（主色）、已完成（绿色）
5. 点击步骤"开始"按钮，跳转到模板填写页
6. 步骤卡片：background: var(--gray-0); border: 1px solid var(--gray-150); border-radius: 8px;
7. 已完成步骤显示勾选图标和"已完成"标签
```

实现模板 CRUD 路由：

```text
实现 SparkLab 的模板 CRUD 路由：
1. 创建 server/routers/template_router.py（普通用户）和 server/routers/admin/template_admin_router.py（管理员）
2. 使用 sparklab.services.template_service 处理业务逻辑
3. 使用 sparklab.repositories.template_repository 封装数据库查询
4. 管理员路由使用 get_current_admin 依赖注入
5. 支持分页、搜索、标签筛选
6. 删除操作为软删除，更新 status 为 archived
7. Pydantic schemas 定义在 sparklab.schemas
8. 错误响应格式统一
```