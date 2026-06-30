"""HTTP 路由层入口。

所有领域路由在此集中注册，main.py 只引用 `router` 即可。
保持路由层薄：每个 *_router.py 文件只做请求解析、依赖注入和响应装配；
业务逻辑放到 sparklab.services，数据查询放到 sparklab.repositories。
"""

from fastapi import APIRouter

from server.routers.activation_router import activation
from server.routers.admin import admin_router
from server.routers.auth_router import auth
from server.routers.playbook_router import playbook
from server.routers.system_router import system
from server.routers.tag_router import tag
from server.routers.template_router import template

router = APIRouter()

# 基础系统接口
router.include_router(system)  # /api/system/*

# 认证与激活
router.include_router(auth)  # /api/auth/*
router.include_router(activation)  # /api/activation/*

# 标签
router.include_router(tag)  # /api/tags/*

# 模板
router.include_router(template)  # /api/templates/*

# 工作流
router.include_router(playbook)  # /api/playbooks/*

# 管理后台
router.include_router(admin_router)  # /api/admin/*

# 后续随业务模块陆续接入：
# router.include_router(favorites)   # /api/favorites/*
# router.include_router(news)        # /api/news/*
# router.include_router(ai_platforms)  # /api/ai-platforms/*
