---
name: sparklab-auth-bearer-header
description: SparkLab 鉴权方式 - JWT + Bearer Header（与 Yuxi 一致），2026-06-25 改自最初的 Cookie 方案
metadata: 
  node_type: memory
  type: project
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

**SparkLab 鉴权方式**：JWT Token + `Authorization: Bearer <token>` Header + 前端 localStorage 存储。

**Why**：2026-06-25 项目主理人决定从最初设计的"HttpOnly Cookie"方案改为"Bearer Header"，以与 Yuxi 完全对齐——这样可以直接复用 Yuxi 的前后端鉴权代码模式，团队学习/维护成本最低。

**How to apply**：

1. **后端**
   - `auth_middleware.get_current_user` 用 `authorization: str | None = Header(default=None)` 读 Header
   - 解析逻辑：检查 `authorization.startswith("Bearer ")`、提取 token、验签、查 Redis 黑名单、查 User 表
   - 路由抛 401 时返回 `WWW-Authenticate: Bearer` Header
   - `Settings` 中**没有** `cookie_*` 字段（已在 2026-06-25 删除）；只有 `jwt_secret` / `jwt_algorithm` / `jwt_expire_minutes`
   - CORS 设置 `allow_credentials=False`，允许 `Authorization` 头
   - 登出：把 token 的 `jti` 写入 Redis `blacklist:<jti>` 键，TTL = 原 Token 剩余有效期

2. **前端（待阶段 2 实现）**
   - 登录成功后把 token 写入 localStorage（key 例如 `sparklab_token`）
   - 请求拦截器（在 `web/src/apis/base.js`）注入 `Authorization: Bearer <token>` Header
   - 拦截 401 → 清 localStorage → 跳 `/login`
   - "记住我"用 localStorage，否则用 sessionStorage（或写入时附带 expiresAt 软到期）

3. **三份设计文档** 已同步修订（2026-06-25）：
   - `docs/SparkLab-产品设计文档.md` §8.1 Token 机制
   - `ARCHITECTURE.md` 认证与激活章节 + 架构不变量
   - `AGENTS.md` 后端开发规范 + Agent Prompt Guide

**反例（不要再写）**：
- 不要在 `Settings` 里加 cookie_name / cookie_samesite / cookie_secure / cookie_domain 字段
- 后端响应不要 `Set-Cookie`
- CORS 不要开 `allow_credentials=True`
- 前端不要用 `credentials: 'include'`
- auth_middleware 不要从 `request.cookies` 取 token

相关：[[sparklab-dev-constraints]]、[[yuxi-reference-mapping]]、[[sparklab-project-overview]]
