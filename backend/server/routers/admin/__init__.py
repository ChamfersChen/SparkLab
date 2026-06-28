
"""管理员路由入口。

所有管理员路由都在 /api/admin/* 之下，依赖 get_current_super_admin 确保权限。
"""

from fastapi import APIRouter

from server.routers.admin.activation_code_admin_router import activation_code_admin
from server.routers.admin.admin_account_router import admin_account
from server.routers.admin.tag_admin_router import tag_admin
from server.routers.admin.template_admin_router import template_admin

admin_router = APIRouter(prefix="/admin", tags=["admin"])
admin_router.include_router(activation_code_admin)
admin_router.include_router(tag_admin)
admin_router.include_router(template_admin)
admin_router.include_router(admin_account)

