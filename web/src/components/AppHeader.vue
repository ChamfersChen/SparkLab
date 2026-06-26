<script setup>
/**
 * 应用顶栏 - 所有登录后页面共用。
 *
 * 职责：
 * - 品牌 Logo（点击回到 /）
 * - 当前用户身份展示（用户名 + 角色徽标）
 * - 用户菜单（含"退出登录"占位项；真实接入留到 Phase 4）
 *
 * 注意：本组件不假设业务模块入口位置，避免与 DashboardView 的卡片重复。
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, LogIn } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()

const ROLE_META = {
  super_admin: { label: '超管', color: 'red' },
  admin: { label: '管理员', color: 'orange' },
  user: { label: '用户', color: 'default' }
}

const roleMeta = computed(() => ROLE_META[userStore.user?.role] || ROLE_META.user)

function handleLogout() {
  // TODO(Phase 4): 调用后端 /api/auth/logout，把 jti 加入 Redis 黑名单
  userStore.logout()
  router.push({ name: 'login' })
}

function handleLogin() {
  // TODO(Phase 4): router.push({ name: 'login' })
  // 当前 UI 阶段不触发跳转
  console.info('[stub] AppHeader 登录按钮点击')
}
</script>

<template>
  <header class="app-header">
    <router-link to="/" class="brand">
      <Zap :size="20" :stroke-width="2.25" />
      <span>SparkLab</span>
    </router-link>

    <div class="header-right">
      <a-dropdown v-if="userStore.user" placement="bottomRight">
        <span class="user-trigger">
          <span class="username">{{ userStore.user.username }}</span>
          <a-tag :color="roleMeta.color" class="role-tag">{{ roleMeta.label }}</a-tag>
        </span>
        <template #overlay>
          <a-menu>
            <a-menu-item key="logout" @click="handleLogout">退出登录</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
      <a-button v-else type="primary" ghost size="small" class="login-btn" @click="handleLogin">
        <template #icon><LogIn :size="14" :stroke-width="2.25" /></template>
        登录
      </a-button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 32px;
  background: var(--gray-0);
  border-bottom: 1px solid var(--gray-50);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  text-decoration: none;
  letter-spacing: 0.2px;
}

.brand :deep(svg) {
  color: var(--main-color);
}

.brand:hover {
  color: var(--main-700);
}

.header-right {
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.user-trigger:hover {
  background: var(--gray-10);
}

.username {
  font-size: 14px;
  color: var(--color-text);
  font-weight: 500;
}

.role-tag {
  margin: 0;
}

.login-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 32px;
  border-radius: 6px;
}

@media (max-width: 640px) {
  .app-header {
    padding: 0 16px;
  }
}
</style>
