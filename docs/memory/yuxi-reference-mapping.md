---
name: yuxi-reference-mapping
description: 从 reference-projects/Yuxi 借鉴哪些骨架模式，哪些必须剥离掉
metadata: 
  node_type: memory
  type: reference
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

Yuxi (`reference-projects/Yuxi/`) 是 LangGraph + Vue.js + FastAPI + LightRAG 的知识库+智能体平台，**远比 SparkLab 复杂**。仅作为骨架参考。

**可以借鉴的骨架模式**：
- 目录组织：`backend/server`（HTTP 适配） + `backend/package/yuxi`（业务包）→ SparkLab 对应 `backend/package/sparklab`
- `server/main.py` 的 FastAPI 应用结构、CORS 处理、登录限流中间件、`/api` 统一前缀
- `server/routers/__init__.py` 集中注册路由的方式
- `server/utils/auth_middleware.py` 的 `get_db / get_current_user / get_required_user / get_admin_user / get_superadmin_user` 依赖注入链
- `server/utils/lifespan.py` 的应用启动时初始化（建表、初始化超管、初始化默认数据）模式
- `backend/package/yuxi/storage/postgres/manager.py`（pg_manager）管理异步连接池的模式
- `web/src/apis/base.js` 的 `apiRequest / apiGet / apiPost / apiAdminGet ...` 分级请求封装（**直接复用 Bearer Header 鉴权**，与 Yuxi 一致；见 [[sparklab-auth-bearer-header]]）
- Windows 兼容代码：`main.py` 顶部的 `WindowsSelectorEventLoopPolicy` 设置（项目主机是 Windows）
- 前端 stack 选型：Ant Design Vue 4 + Pinia + pinia-plugin-persistedstate + vue-router + lucide-vue-next + markdown-it + dompurify + dayjs + less

**SparkLab 不需要的 Yuxi 能力（必须剥离）**：
- LangGraph / LangChain / 智能体编排（agents, agents/backends, chatbot, subagent）
- 知识库 / 向量库 / 图谱（knowledge, graph, milvus, neo4j, lightrag）
- MCP / Skills / Tools 体系
- Sandbox provisioner（沙箱执行容器）
- MinIO（SparkLab 暂不需要文件存储；如需头像可考虑后期再加，初期用纯 URL）
- 文档解析（mineru-api, paddlex）
- 部门 (Department) 体系 —— SparkLab 管理员之间不做内容归属隔离
- OIDC 第三方登录 —— SparkLab 只走激活码 + 用户名/密码
- API Key / CLI Auth —— SparkLab 用户不需要这些
- 用户登录失败锁定机制可以**简化**，但保留限流中间件

**鉴权方式**：与 Yuxi 一致，都用 `Authorization: Bearer <token>` Header + 前端 localStorage。
（2026-06-25 项目主理人决定从原计划的"HttpOnly Cookie"改为"Bearer Header"以与 Yuxi 对齐，
便于团队复用 Yuxi 的前后端鉴权代码模式。）

直接借鉴 Yuxi `base.js` 的 `getAuthHeaders()` 与 401 自动登出逻辑即可，不需要做 Cookie 改造。

详情见 [[sparklab-auth-bearer-header]]。

参考用户使用方式：用户在对话中要求"参考 Yuxi 的 X"时，定位到对应路径再读。

相关：[[sparklab-project-overview]]、[[sparklab-dev-constraints]]
