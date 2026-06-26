# SparkLab

![status](https://img.shields.io/badge/status-骨架完成%20·%20阶段4%20开发中-blue) ![python](https://img.shields.io/badge/python-3.12+-3776ab?logo=python&logoColor=white) ![vue](https://img.shields.io/badge/vue-3.5-42b883?logo=vuedotjs&logoColor=white)

> AI 内容运营平台 —— 把繁杂的 AI 操作收敛为可复用的模板与剧本，让团队的提示词资产沉淀下来。

---

## 它是什么

SparkLab 是一个 **AI 内容运营平台**：

- 管理员发布**提示词模板**（五段式 Role/Goal/Input/Output/Example）、**Playbook 剧本**（多步骤顺序排列）和**资讯**
- 付费用户持**激活码邀请链接**完成注册
- 用户在前端按表单填空生成专业提示词，**复制到第三方 AI 平台**（DeepSeek / Kimi / 豆包 / 通义千问）使用

> 完整产品规格见 [`docs/SparkLab-产品设计文档.md`](docs/SparkLab-产品设计文档.md)。

## 不做什么（边界）

明确地不实现以下能力，避免误解：

- ❌ **不内置 AI 生成** —— 系统不调任何 LLM，仅生成可拷贝的提示词
- ❌ **不开放公开注册** —— 仅激活码邀请准入
- ❌ **不做评论 / 评分 / 社区** —— 是工具，不是社区
- ❌ **工作流变量不自动传递** —— 每步独立填表（极简模式）

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + Pinia + Ant Design Vue 4 + lucide-vue-next，pnpm 管理 |
| 后端 | FastAPI + Python 3.12+，分层 `routers → services → repositories → models` |
| 存储 | Postgres 16（业务数据）+ Redis 7（JWT 黑名单 / 缓存） |
| 鉴权 | JWT + `Authorization: Bearer` Header（前端 localStorage 存储） |
| 编排 | 后端 Docker Compose（API 宿主机端口 **5151**），前端本机 `pnpm dev`（**5173**） |
| 迁移 | Alembic（lifespan 启动时自动 `upgrade head`） |

## 项目状态（2026-06-26）

- ✅ **阶段 0-3 完成**：项目骨架就绪，后端测试全部通过
- ✅ **阶段 4 完成**：认证 + 激活码 + 标签模块（含 e2e 测试）
- ✅ **阶段 5 部分完成**：前端登录/激活页 UI + API 封装
- ✅ **欢迎页 UI 上线**：`/` 为 public，Hero CTA 按登录态切换，4 张业务模块入口卡（骨架阶段 disabled）
- 🛠 **阶段 6 待开发**：业务模块（模板/Playbook/资讯/收藏/看板）

骨架阶段任务追踪见 [`docs/2026-06-25-项目骨架搭建.md`](docs/2026-06-25-项目骨架搭建.md)。

## 快速开始

### 前置条件

- Docker Desktop（含 Docker Compose）
- Node.js 20+ 与 pnpm 9+（前端在本机跑）
- 已构建好基底镜像 `base-api:0.1.0`（包含系统依赖与 uv，由项目主理人维护）

### 5 步启动

```bash
# 1. 克隆并准备环境变量
git clone <repo-url> SparkLab && cd SparkLab
cp .env.template .env
# 修改 .env：JWT_SECRET、INITIAL_SUPERADMIN_PASSWORD、数据库账号等

# 2. 构建后端镜像（首次需要）
make build

# 3. 启动后端三件套（api-dev + postgres + redis）
make up

# 4. 启动前端（本机，新开终端）
cd web
pnpm install     # 首次或 package.json 变更后
pnpm dev

# 5. 浏览器打开
# 前端：http://localhost:5173
# 后端 health：http://localhost:5151/api/system/health
```

> 前端 Vite 默认把 `/api/*` 反代到 `http://localhost:5151`，可通过 `VITE_API_URL` 覆盖。

## 项目结构

```
SparkLab/
├── backend/
│   ├── server/                 # FastAPI HTTP 层：路由 / 中间件 / lifespan
│   └── package/sparklab/       # 业务包：services / repositories / models / schemas / storage
├── web/src/                    # Vue 3 应用：router / apis / stores / views / components
├── docker/                     # Dockerfile + 数据卷挂载点
├── docs/                       # 产品文档 / 设计规范 / 任务文档 / memory
└── reference-projects/Yuxi/    # 仅作骨架借鉴的参考项目（只读）
```

代码地图与目录职责详见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

## 常用命令

来自项目根 [`Makefile`](Makefile)：

| 命令 | 作用 |
|---|---|
| `make up` / `make down` | 启停后端容器组 |
| `make ps` / `make logs` | 查看服务状态 / 跟随全部日志 |
| `make api-logs` | 跟随 API 日志（最常用） |
| `make shell-api` | 进入 api-dev 容器 |
| `make shell-db` | 进入 Postgres psql |
| `make test` | 运行后端全套测试（unit + integration + e2e） |
| `make lint` / `make format` | ruff 检查 / 格式化 |
| `make migrate` | 应用 Alembic 迁移到最新 |
| `make revision m="说明"` | 自动生成新迁移 |

前端命令在 `web/` 目录下：`pnpm dev` / `pnpm lint` / `pnpm format` / `pnpm build`。

## 文档导航

| 文档 | 何时读 |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 改动前先看代码地图与架构边界 |
| [`AGENTS.md`](AGENTS.md) | 接手项目 / 提交代码前看开发约定 |
| [`docs/SparkLab-产品设计文档.md`](docs/SparkLab-产品设计文档.md) | 实现具体业务模块前对齐需求 |
| [`docs/design.md`](docs/design.md) | 写前端 UI 前看设计 token 与组件规范 |
| [`docs/2026-06-25-项目骨架搭建.md`](docs/2026-06-25-项目骨架搭建.md) | 了解骨架建设过程与决策 |
| [`docs/memory/`](docs/memory) | 历次会话沉淀的项目共识（约束、坑、参考映射） |

## 开发约定

提交代码前请阅读 [`AGENTS.md`](AGENTS.md)，核心要求：

- **路由薄、领域厚**：HTTP 路由只做请求适配，业务逻辑落在 `sparklab.services`，数据库访问落在 `sparklab.repositories`
- **后端必配套测试**：每个模块完成时同步补 unit / integration / e2e（见 [`docs/memory/sparklab-backend-must-test.md`](docs/memory/sparklab-backend-must-test.md)）
- **前端 API 集中**：所有后端调用必须封装在 `web/src/apis`，组件不许散落拼 URL
- **样式 token 化**：颜色一律走 `web/src/assets/css/base.css` CSS 变量
- **不做过度防御** —— 错误要及时暴露和修复，不用冗余兜底吞掉
- **提交信息**：Conventional Commits + 中文

## 反馈

项目处于活跃开发期。请通过仓库 issue 提交反馈，或联系项目主理人。
