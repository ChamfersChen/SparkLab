# SparkLab ARCHITECTURE.md

本文档是 SparkLab 的代码地图，参考 matklad 的 `ARCHITECTURE.md` 建议维护：只描述相对稳定的系统边界、目录职责和跨切面约束，避免同步易变的实现细节。新贡献者如果不确定"某个能力应该改哪里"，先读这里，再用符号搜索定位具体类型、函数或路由。

## 鸟瞰

SparkLab 是一个 AI 内容运营平台，为内容创作者提供提示词模板和工作流 Playbook 的管理与使用功能。管理员发布「提示词模板」和「模板工作流 Playbook」和资讯；付费用户持激活码激活账号，按工作流步骤逐步填空生成提示词，复制到第三方 AI 平台使用。

开发与运行拓扑以 `docker-compose.yml` 为准。核心开发服务包括：

- `api-dev`：FastAPI API 服务，挂载 `backend/server` 和 `backend/package/sparklab` 并热重载。容器内监听 5050，通过 Compose 映射到宿主机 **5151**。
- `postgres`：承载业务数据（用户、模板、工作流、标签、资讯、激活码等）。
- `redis`：承载 JWT Token 黑名单、缓存和会话状态。

前端开发服务（**本机运行**，不再走容器）：

- `web-dev`：Vue/Vite，本机 `cd web && pnpm dev`，监听 5173。`vite.config.js` 把 `/api/*` 反代到 `http://localhost:5151`（API 宿主机端口），可由 `VITE_API_URL` 覆盖。`docker-compose.yml` 中的 `web-dev` 服务定义已注释保留，便于将来重启用。

## 后端代码地图

后端分成两个顶层边界：`backend/server` 是 Web 应用入口与 HTTP 适配层，`backend/package/sparklab` 是可复用业务包。新增业务逻辑通常优先放在 `sparklab` 包中，路由层只做请求解析、认证上下文和响应装配。

- `server/main.py` 创建 FastAPI 应用，注册中间件，并把所有业务接口统一挂到 `/api`。
- `server/routers` 是 HTTP 路由边界。路由按领域拆分，集中在 `server/routers/__init__.py` 注册；管理员接口放在 `admin` 子目录，普通用户接口直接放在 `routers` 下。
- `server/utils` 放 Web 层通用能力，例如生命周期、认证、日志与迁移辅助。

`backend/package/sparklab` 是后端主体：

- `services` 是用例层，负责串联 repositories 和外部系统。认证、模板管理、工作流管理、标签管理、资讯管理、收藏、数据统计等跨模块流程都从这里找入口。
- `repositories` 是数据库访问边界，封装业务对象的 SQLAlchemy 查询。不要让路由绕过 repository 直接操作模型。
- `storage` 放持久化基础设施。`storage/postgres` 管理业务表和连接池；`storage/redis` 管理缓存和 Token 黑名单。
- `models` 定义 SQLAlchemy 模型，包括用户、激活码、模板、标签、模板-标签关联、工作流、工作流步骤、收藏、资讯、第三方 AI 平台等。
- `schemas` 定义 Pydantic 数据结构，用于请求/响应验证和数据传输。
- `auth` 封装认证与权限逻辑，包括 JWT Token 生成与验证、激活码校验、角色权限检查。
- `utils` 放跨领域但足够通用的工具。

测试代码放在 `backend/test`，按 `unit`、`integration`、`e2e` 分层组织。新增或修改后端行为时，测试应落在最能覆盖风险的那一层。

## 前端代码地图

前端是 Vue 3 + Vite 应用，业务入口集中在 `web/src`。

- `main.js` 挂载应用，`App.vue` 是根组件。
- `router` 定义页面路由和权限跳转。**公开页**：欢迎页（`/`）、登录页（`/login`）、激活页（`/activate`）、404；**受保护页**：业务模块（模板库、工作流、资讯、收藏、个人中心、后台管理等），未登录访问会被守卫跳转到 `/login`。
- `apis` 是唯一推荐的后端接口封装位置。新增后端接口时，同步在这里补对应 API 方法，复用 `base.js` 的请求、鉴权和错误处理。
- `stores` 放 Pinia 状态，例如用户信息、主题、侧边栏展开状态。
- `views` 是页面级入口，`components` 是可复用界面块。当前已实现的通用组件：
  - `components/AppHeader.vue` — 通用顶栏（Logo + 用户菜单/登录按钮 + 角色徽标），所有登录后页面共用。
  - `components/ModuleCard.vue` — 业务模块入口卡（icon/title/subtitle/badge/disabled），Dashboard 首页与未来工作台页可复用。
- `composables` 放可组合的前端运行逻辑，例如提示词变量解析、工作流步骤状态管理、第三方平台跳转。
- `utils` 放前端通用工具和轻量转换逻辑；样式集中在 `assets/css`，颜色和基础规范优先复用 `base.css` 与现有 less 文件。

## 核心模块详解

### 认证与激活

- **激活码验证**：前端读取 URL 中的 `code` 参数，调用 `POST /api/activation/verify` 验证；验证通过后显示设置账号表单。
- **账号创建**：用户提交用户名和密码，后端标记激活码为"已使用"，创建用户并签发 JWT Token（响应体返回，前端写入 localStorage）。
- **登录认证**：用户输入用户名/密码，后端验证后生成 JWT Token，在响应体中返回；前端写入 localStorage，后续请求通过 `Authorization: Bearer <token>` Header 携带。
- **Token 刷新**：前端拦截 401 响应，自动调用刷新接口获取新 Token。
- **权限控制**：后端路由依赖注入 `get_current_user` 获取当前用户，`get_current_admin` 确保管理员权限。

### 模板管理

- **五段式结构**：模板包含 Role（角色定义）、Goal（目标说明）、Input（变量定义）、Output（输出要求）、Example（示例效果）。
- **变量解析**：模板使用 `{{变量名}}` 语法定义变量，前端自动生成表单输入框。
- **variable_hints**：每个变量可配置填写提示，指导用户正确输入。
- **软删除**：模板删除时只更新 `status` 为 `archived`，不物理删除。
- **使用统计**：用户点击"生成提示词"时，模板 `use_count` +1。

### 工作流 Playbook

- **工作流定义**：工作流是模板的顺序排列，包含标题、描述和步骤列表。
- **步骤关联**：每个步骤关联一个模板，按 `step_order` 顺序执行。
- **极简模式**：每步独立，变量不自动传递；用户完成一步后手动进入下一步。
- **步骤状态**：前端管理步骤状态（未开始/当前/已完成），不持久化到后端。
- **使用统计**：用户首次进入工作流运行页时，工作流 `use_count` +1。

### 标签体系

- **三维标签**：平台（Platform）、内容类型（ContentType）、行业场景（Industry）。
- **动态配置**：管理员可在后台增删改标签，通过 `sort_order` 控制排序。
- **多对多关系**：模板与标签通过 `template_tags` 关联表建立多对多关系。

### 资讯管理

- **Markdown 格式**：资讯正文使用 Markdown 格式存储和渲染。
- **状态管理**：草稿（draft）/ 已发布（published）/ 已归档（archived）。

### 收藏功能

- **模板收藏**：用户可收藏模板，通过 `favorites` 表建立用户与模板的关联。
- **联合唯一约束**：同一用户不能重复收藏同一模板。

### 数据看板

- **核心指标**：模板总数、工作流总数、资讯总数、累计使用次数、累计收藏数、用户总数、激活码统计。
- **使用排行**：模板使用排行榜、工作流使用排行榜。
- **动态时间线**：近期发布动态（模板/工作流/资讯）。

### 欢迎页（Dashboard 首页 `/`）

- **路由公开**：`meta.public = true`，未登录也能访问；前端不再把 `/` 当作"登录后专属"。
- **Hero 区按登录态切换 CTA**：未登录显示「登录」（primary）+ 注册说明文案；已登录显示「进入系统」（primary）。
- **业务模块入口**：4 张 `ModuleCard`（Prompt 模板 / Playbook 剧本 / AI 资讯 / 管理后台），骨架阶段全部 `disabled` + `敬请期待` badge；管理后台卡仅 `isAdmin/isSuperAdmin` 可见。
- **顶栏**：通用 `AppHeader`，未登录显示「登录」按钮，已登录显示用户名 + 角色徽标 + 退出菜单。
- **业务模块上线方式**：修改 `DashboardView` 中 `ALL_MODULES` 数组的对应项，把 `disabled` 改为 `false` 并补上 `to/handler`。

## 运行链路

### 用户首次使用（激活 + 登录）

1. 用户点击激活链接，前端读取 URL 中的 `code` 参数。
2. `web/src/apis/activation.js` 调用 `POST /api/activation/verify`。
3. `server/routers/auth_router.py` 进入后端，委托 `sparklab.services.auth_service.verify_activation_code`。
4. 服务层验证激活码状态，有效则返回验证成功。
5. 前端显示设置账号表单，用户提交用户名和密码。
6. `POST /api/activation/activate` 创建用户，标记激活码为已使用，生成 JWT Token。
7. 后端在响应体返回 Token，前端写入 localStorage，跳转到欢迎页（`/`）后由用户点击"进入系统"进入业务区。

### 用户使用工作流完成创作

1. 用户在欢迎页（`/`）点击"进入系统"进入业务区，再从工作流列表选中一个 Playbook。
2. `web/src/views/PlaybookRun.vue` 加载工作流详情和步骤列表。
3. `GET /api/playbooks/:id` 获取工作流信息，包含关联的步骤和模板。
4. 用户点击某步骤的"开始"按钮，进入提示词填写页。
5. 前端解析模板中的 `{{变量名}}`，生成表单输入框。
6. 用户填写表单，点击"生成提示词"。
7. 前端拼接变量，生成完整 Prompt，显示在预览区域。
8. 用户点击"复制提示词"，内容复制到剪贴板。
9. 用户点击第三方 AI 平台快捷按钮，新标签页打开对应平台。
10. 用户手动标记步骤为"已完成"，进入下一步。

### 管理员发布模板

1. 管理员进入后台管理，点击"新建模板"。
2. `web/src/views/admin/TemplateManage.vue` 显示模板编辑表单。
3. 管理员填写五段式内容和三维标签。
4. `POST /api/admin/templates` 创建模板，保存到数据库。
5. 模板状态为 `draft`，管理员可预览后发布。

## 架构不变量

- Docker Compose 是开发环境的事实来源。开发时优先检查容器、日志和热重载，不要默认要求本地裸跑服务。
- HTTP 路由层应保持薄；领域流程放在 `sparklab.services`，持久化查询放在 `sparklab.repositories`。
- 前端 API 调用应集中在 `web/src/apis`，组件不要散落拼接后端 URL。
- 认证使用 JWT Token + `Authorization: Bearer` Header；前端 localStorage 存储；登出后 Token `jti` 进入 Redis 黑名单直到自然过期。
- 模板和工作流使用软删除策略，只更新 `status` 字段，不物理删除。
- 工作流步骤状态由前端管理，不持久化到后端（极简模式）。
- 面向用户或外部系统的输入在边界校验；内部服务之间优先信任已有类型、仓储和框架约束。

## 跨切面关注点

- **配置**：环境变量来自 Compose 和 `.env`，包括数据库连接、JWT Secret、Redis 连接等。
- **权限**：前端路由守卫提供页面级跳转，后端认证与权限检查仍是最终边界。普通用户只能浏览和使用，不能发布或评论。
- **状态与存储**：Postgres 存业务数据，Redis 承载 Token 黑名单和缓存。
- **日志**：后端使用标准 logging 模块，日志格式统一，包含请求 ID。
- **观测与调试**：开发阶段优先使用 `docker logs api-dev --tail 100` 和现有测试分层定位问题。

## 目录结构

```
backend/
├── server/
│   ├── main.py              # FastAPI 应用入口
│   ├── routers/             # HTTP 路由
│   │   ├── __init__.py      # 路由注册
│   │   ├── auth_router.py   # 认证与激活
│   │   ├── template_router.py # 模板相关
│   │   ├── playbook_router.py # 工作流相关
│   │   ├── tag_router.py    # 标签相关
│   │   ├── news_router.py   # 资讯相关
│   │   ├── favorite_router.py # 收藏相关
│   │   ├── admin/           # 管理员路由
│   │   │   ├── template_admin_router.py
│   │   │   ├── playbook_admin_router.py
│   │   │   ├── tag_admin_router.py
│   │   │   ├── news_admin_router.py
│   │   │   ├── activation_code_router.py
│   │   │   ├── admin_router.py
│   │   │   └── platform_router.py
│   └── utils/               # Web 层通用工具
└── package/
    └── sparklab/
        ├── services/        # 用例层
        │   ├── auth_service.py
        │   ├── template_service.py
        │   ├── playbook_service.py
        │   ├── tag_service.py
        │   ├── news_service.py
        │   ├── favorite_service.py
        │   └── dashboard_service.py
        ├── repositories/    # 数据访问层
        │   ├── user_repository.py
        │   ├── template_repository.py
        │   ├── playbook_repository.py
        │   ├── tag_repository.py
        │   ├── news_repository.py
        │   └── activation_code_repository.py
        ├── storage/         # 持久化基础设施
        │   ├── postgres/
        │   └── redis/
        ├── models/          # SQLAlchemy 模型
        ├── schemas/         # Pydantic 数据结构
        ├── auth/            # 认证与权限
        └── utils/           # 通用工具

web/
└── src/
    ├── main.js              # Vue 应用入口
    ├── App.vue              # 根组件
    ├── router/              # 路由配置（欢迎页/登录/激活 public，其余受保护）
    ├── apis/                # 后端接口封装（base.js + 各模块）
    ├── stores/              # Pinia 状态管理（user / theme）
    ├── views/               # 页面级组件
    │   ├── DashboardView.vue  # 欢迎页（public，按登录态切换 CTA + 业务模块入口）
    │   ├── LoginView.vue
    │   ├── ActivateView.vue
    │   ├── NotFoundView.vue
    │   └── （后续：templates/ playbooks/ news/ favorites/ profile/ admin/）
    ├── components/          # 可复用组件
    │   ├── AppHeader.vue      # 通用顶栏（Logo + 用户菜单/登录按钮）
    │   └── ModuleCard.vue     # 业务模块入口卡
    ├── composables/         # 可组合逻辑
    ├── utils/               # 前端工具
    └── assets/
        └── css/             # 样式文件（base.css token + dark 覆盖 + main.css）
```