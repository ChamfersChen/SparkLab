"""HTTP 路由层入口。

所有领域路由在此集中注册，main.py 只引用 `router` 即可。
保持路由层薄：每个 *_router.py 文件只做请求解析、依赖注入和响应装配；
业务逻辑放到 sparklab.services，数据查询放到 sparklab.repositories。
"""

from fastapi import APIRouter

from server.routers.system_router import system

router = APIRouter()

# 基础系统接口
router.include_router(system)  # /api/system/*

# 后续随业务模块陆续接入：
# router.include_router(auth)        # /api/auth/*
# router.include_router(activation)  # /api/activation/*
# router.include_router(templates)   # /api/templates/*
# router.include_router(playbooks)   # /api/playbooks/*
# router.include_router(tags)        # /api/tags/*
# router.include_router(favorites)   # /api/favorites/*
# router.include_router(news)        # /api/news/*
# router.include_router(ai_platforms)  # /api/ai-platforms/*
# 管理员相关路由集中在 routers/admin/ 子目录
