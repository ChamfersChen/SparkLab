---
name: sparklab-homepage-is-welcome-page
description: 首页 `/` 是 public 欢迎页（Landing+Hub 性质），按登录态切换 Hero CTA，下方是业务模块入口
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 715cefc0-c1a6-4ffe-b33c-199a4e7c0eb8
---

**首页 `/` 的当前定义（2026-06-26 起）**：

`DashboardView.vue` 是 **public 欢迎页**（`meta.public = true`），承担两个职责：
1. **品牌 / 产品介绍**：未登录访客看 → 这是个什么平台、注册门槛是激活码邀请
2. **登录后业务入口**：已登录用户看 → 欢迎回来 + 业务模块入口卡 + "进入系统"CTA

**信息架构**：
```
public 欢迎页 (/)
  ├─ AppHeader（Logo + 登录按钮 / 用户菜单）
  ├─ Hero
  │   ├─ greeting："欢迎来到 SparkLab" ↔ "欢迎回来，{username}"
  │   ├─ subtitle：访客口径 ↔ 工作台口径
  │   └─ CTA：[登录] ↔ [进入系统]
  ├─ 业务模块入口区（4 张 ModuleCard）
  │   ├─ Prompt 模板 / Playbook 剧本 / AI 资讯（全员可见）
  │   └─ 管理后台（仅 isAdmin/isSuperAdmin 可见）
  ├─ 平台标签条（DeepSeek / Kimi / 豆包 / 通义千问）
  └─ 阶段提示（骨架期显示，业务模块上线后移除）
```

**业务模块上线方式**：改 `ALL_MODULES` 数组中对应项的 `disabled: false` 并补 `to/handler`，无需改 template/CSS。

**首页不是**：
- ❌ 不是带左侧导航的 Dashboard 工作台（左侧导航在业务模块页用）
- ❌ 不堆假数据（不展示"推荐工作流"/"热门模板"，除非业务模块已上线有真实数据）
- ❌ 不做"进入系统"两段式跳转的复杂流程（CTA 直接跳首个业务模块，如 templates 列表）

**与最初设想的偏离**：
- 最初定义为"登录后的纯 landing"（强制鉴权 + "进入系统" 两段式）
- 现实演化为"public 欢迎页 + 按态切换"（合二为一，节省一次跳转，未登录用户也能看到产品信息）

相关：[[sparklab-dev-constraints]]、[[sparklab-project-overview]]
