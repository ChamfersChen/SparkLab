---
name: sparklab-project-overview
description: SparkLab 平台定位、技术栈和核心模块速查，新会话开工前先读
metadata: 
  node_type: memory
  type: project
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

**产品定位**：AI 内容运营平台。管理员发布「提示词模板（五段式 Role/Goal/Input/Output/Example）」+「工作流 Playbook（多步骤顺序排列）」+「资讯」 → 付费用户持激活码激活账号 → 按工作流步骤逐步填空生成提示词 → 复制到第三方 AI 平台（DeepSeek/Kimi/豆包/通义千问）使用。

**关键边界（不做的事）**：
- 不内置 AI 生成（系统不调 LLM）
- 不开放公开注册（激活码准入）
- 不做用户评论 / 评分 / 社区
- 不做工作流变量自动传递（极简模式，每步独立填表）
- 不做付费会员体系（schema 预留扩展）

**技术栈**：
- 前端：Vue 3 + Vite + Pinia + Ant Design Vue + LESS + lucide-vue-next，pnpm 管理
- 后端：FastAPI + Python 3.12+，分层 routers → services → repositories → models
- 存储：Postgres（业务数据）+ Redis（JWT 黑名单/缓存）
- 编排：Docker Compose（事实来源），api-dev 和 web-dev 热重载

**三类角色**：
- super_admin：全部 + 激活码 / 管理员账号 / AI 平台配置
- admin：模板 / 工作流 / 资讯 / 标签 / 数据看板（管理员之间不做内容归属隔离）
- user：浏览、收藏、用模板/工作流生成提示词；不能发布、不能评论

**十大核心模块**：激活与认证、模板管理、工作流 Playbook、三维标签体系（platform/content_type/industry）、资讯管理、收藏、激活码管理、管理员账号管理、第三方 AI 平台配置、数据看板。

**主色**：科技蓝 `#3B82F6`（`--main-color`）。布局：左侧固定导航 220px + 右侧自适应。

**项目状态（2026-06-26）**：
- ✅ 阶段 0-3 完成：项目骨架搭建完毕，首次集成验证通过
- ✅ 阶段 4 完成：认证 + 激活码 + 标签模块（含后端路由/服务/仓储/模型/迁移 + e2e 测试）
- ✅ 阶段 5 部分完成：前端登录/激活页 UI + auth/activation/tag API 封装
- 🟡 阶段 6 进行中：标签管理页 UI 已修复 template 错误，其他业务模块（模板/Playbook/资讯/收藏/看板）待开发
- ✅ 后端：FastAPI + SQLAlchemy + Alembic + Redis，本机可跑全部测试通过
- ✅ 前端：Vue 3 + Vite + Pinia + Ant Design Vue，路由守卫就绪
- ✅ 欢迎页（`/`）：public，Hero CTA 按登录态切换，4 张业务模块入口卡（骨架阶段 disabled）；通用 `AppHeader` + `ModuleCard` 组件已抽出
- ✅ 认证方式：JWT + Bearer Header（前端 localStorage 存储）
- 🛠 运行拓扑：后端 Docker Compose（API 宿主机端口 **5151**），前端本机 `pnpm dev`（5173）；`docker-compose.yml` 中 `web-dev` 服务已注释保留

**相关文档**：`AGENTS.md`、`ARCHITECTURE.md`、`docs/SparkLab-产品设计文档.md`、`docs/design.md`、`docs/2026-06-25-项目骨架搭建.md`。
开发约束细节见 [[sparklab-dev-constraints]]，Yuxi 参考对照见 [[yuxi-reference-mapping]]，认证方式见 [[sparklab-auth-bearer-header]]，欢迎页定义见 [[sparklab-homepage-is-welcome-page]]。
