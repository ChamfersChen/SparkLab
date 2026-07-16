<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Zap, LogIn } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { logout as apiLogout } from '@/apis/auth_api'

const userStore = useUserStore()
const router = useRouter()

const ROLE_META = {
  super_admin: { label: '超管', color: 'red' },
  admin: { label: '管理员', color: 'orange' },
  user: { label: '用户', color: 'default' },
}

const roleMeta = computed(() => ROLE_META[userStore.user?.role] || ROLE_META.user)

async function handleLogout() {
  try {
    await apiLogout()
  } catch {
    // 即使后端登出失败也清除本地状态
  }
  userStore.logout()
  router.push({ name: 'login' })
}

function handleLogin() {
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="app-header">
    <router-link to="/" class="brand">
      <!-- <Zap :size="20" :stroke-width="2.25" /> -->
      <img src="/favicon-g.svg" alt="logo" width="35" height="35" />
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
