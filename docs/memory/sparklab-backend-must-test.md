---
name: sparklab-backend-must-test
description: 写完后端功能必须补单元测试 + 集成测试，不要等用户提醒
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

写完任何后端功能（模块、路由、服务、仓储、工具函数）后，**必须同步在 `backend/test/{unit,integration,e2e}` 对应层级补测试**，不要等用户来提醒。这是 AGENTS.md §4 明确写的"开发完成必须：检查 → 测试 → Lint"流程，但容易在追求"先把骨架/功能跑起来"时漏掉。

**Why**：用户在 2026-06-25 阶段 1 骨架交付时指出"阶段一你需要写单元测试呀"——当时 28 个文件全部写完却没有一个测试用例，违反了项目开发准则。

**How to apply**：

1. 完成一个模块的实现后，**同一轮回应**就要把测试一起写上，不要拆成"先实现 → 等用户提 → 再补"两步
2. 分层判断（参考 [[sparklab-dev-constraints]] 的 test 目录分层）：
   - `unit/` —— 纯函数、Pydantic 模型、配置解析、工具方法 → **几乎所有模块都要有**
   - `integration/` —— 涉及 DB / Redis 真实连接的 repository、service → 改 DB 的模块必加
   - `e2e/` —— HTTP 路由、跨层流程、契约（含 stub 抛 NotImplementedError 的占位契约） → 新增路由时必加
3. 占位/stub 也要写**契约测试**，明确锁定"未实现"状态，等真实实现到位时测试自然失败提醒替换
4. 在收尾汇报里**显式列出测试用例数和分层**，方便用户审阅覆盖面
5. 提醒用户实际跑测试的入口是 `make test`（容器内 `uv run pytest /app/test`），不能本地裸跑

相关：[[sparklab-dev-constraints]]、[[sparklab-project-overview]]
