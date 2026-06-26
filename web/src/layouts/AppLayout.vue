<script setup>
/**
 * 应用主布局 - 左侧固定导航 + 右侧自适应内容区。
 *
 * 导航层级（按产品文档 §2）：
 *   用户端：首页 / 模板库 / 工作流 / 资讯 / 我的收藏 / 个人中心
 *   管理后台（管理员可见）：模板管理 / 工作流管理 / 资讯管理 / 标签管理 / 数据看板
 *   仅超管：激活码管理 / 管理员账号 / AI 平台配置
 *
 * 底部：用户信息 + 退出登录。
 */
import { ref, computed } from 'vue'
import { useRouter, useRoute, RouterView } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  LayoutDashboard,
  FileText,
  BookOpen,
  Newspaper,
  Heart,
  User,
  Settings,
  ClipboardList,
  Tag,
  BarChart3,
  KeyRound,
  Shield,
  Cpu,
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
  ChevronDown
} from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const collapsed = ref(false)

// 用户端导航
const userNavItems = [
  { name: '首页', path: '/templates', icon: LayoutDashboard },
  { name: '模板库', path: '/templates', icon: FileText },
  { name: '工作流', path: '/playbooks', icon: BookOpen },
  { name: '资讯', path: '/news', icon: Newspaper },
  { name: '我的收藏', path: '/favorites', icon: Heart },
  { name: '个人中心', path: '/profile', icon: User },
]

// 管理后台导航
const adminNavItems = computed(() => {
  const items = [
    { name: '模板管理', path: '/admin/templates', icon: FileText },
    { name: '工作流管理', path: '/admin/playbooks', icon: BookOpen },
    { name: '资讯管理', path: '/admin/news', icon: Newspaper },
    { name: '标签管理', path: '/admin/tags', icon: Tag },
    { name: '数据看板', path: '/admin/dashboard', icon: BarChart3 },
  ]
  if (userStore.isSuperAdmin) {
    items.push(
      { name: '激活码管理', path: '/admin/activation-codes', icon: KeyRound },
      { name: '管理员账号', path: '/admin/admins', icon: Shield },
      { name: 'AI 平台配置', path: '/admin/platforms', icon: Cpu },
    )
  }
  return items
})

const isAdminRoute = computed(() =>
  route.path.startsWith('/admin')
)

const isActive = (path) => {
  // 首页 /templates 特殊处理
  if (path === '/templates' && !isAdminRoute.value) {
    return route.path === '/templates' || route.path.startsWith('/templates/')
  }
  return route.path === path || route.path.startsWith(path + '/')
}

function navigate(path) {
  router.push(path)
}

function handleLogout() {
  userStore.logout()
  router.push({ name: 'login' })
}

const roleLabel = computed(() => {
  const map = { super_admin: '超管', admin: '管理员', user: '用户' }
  return map[userStore.user?.role] || '用户'
})
</script>

<template>
  <div class="app-layout" :class="{ collapsed }">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <!-- 品牌区 -->
      <div class="sidebar-brand">
        <router-link to="/" class="brand-link">
          <div class="brand-icon">S</div>
          <span v-show="!collapsed" class="brand-name">SparkLab</span>
        </router-link>
        <button
          class="collapse-btn"
          :title="collapsed ? '展开侧边栏' : '折叠侧边栏'"
          @click="collapsed = !collapsed"
        >
          <PanelLeftClose v-if="!collapsed" :size="16" />
          <PanelLeftOpen v-else :size="16" />
        </button>
      </div>

      <!-- 导航菜单 -->
      <div class="sidebar-nav">
        <!-- 用户端导航 -->
        <div class="nav-section">
          <div v-if="!collapsed" class="nav-section-title">导航</div>
          <router-link
            v-for="item in userNavItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <component :is="item.icon" :size="18" class="nav-icon" />
            <span v-show="!collapsed" class="nav-text">{{ item.name }}</span>
          </router-link>
        </div>

        <!-- 分隔线 -->
        <div v-if="userStore.isAdmin" class="nav-divider" />

        <!-- 管理后台导航 -->
        <div v-if="userStore.isAdmin" class="nav-section">
          <div v-if="!collapsed" class="nav-section-title">管理后台</div>
          <router-link
            v-for="item in adminNavItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <component :is="item.icon" :size="18" class="nav-icon" />
            <span v-show="!collapsed" class="nav-text">{{ item.name }}</span>
          </router-link>
        </div>
      </div>

      <!-- 底部用户区 -->
      <div class="sidebar-footer">
        <div class="user-section">
          <div class="user-avatar">{{ (userStore.user?.username || 'U')[0].toUpperCase() }}</div>
          <div v-show="!collapsed" class="user-info">
            <div class="user-name">{{ userStore.user?.username }}</div>
            <div class="user-role">{{ roleLabel }}</div>
          </div>
          <a-dropdown placement="topRight" :trigger="['click']">
            <button class="user-menu-btn">
              <ChevronDown v-if="!collapsed" :size="14" />
            </button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="navigate('/profile')">
                  <User :size="14" /> 个人中心
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item @click="handleLogout">
                  <LogOut :size="14" /> 退出登录
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>
    </aside>

    <!-- 右侧内容区 -->
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ========== Sidebar ========== */
.sidebar {
  display: flex;
  flex-direction: column;
  width: 220px;
  background: var(--gray-0);
  border-right: 1px solid var(--gray-50);
  flex-shrink: 0;
  transition: width 0.18s ease;
  overflow: hidden;
}

.collapsed .sidebar {
  width: 56px;
}

/* Brand */
.sidebar-brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 12px;
  border-bottom: 1px solid var(--gray-50);
  flex-shrink: 0;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--color-text);
  min-width: 0;
}

.brand-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--main-color);
  color: var(--gray-0);
  border-radius: 6px;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}

.brand-name {
  font-size: 15px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: var(--gray-10);
  color: var(--color-text);
}

/* Navigation */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px 0;
}

.nav-section {
  margin-bottom: 4px;
}

.nav-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding: 8px 8px 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nav-divider {
  height: 1px;
  background: var(--gray-50);
  margin: 8px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 8px;
  margin-bottom: 2px;
  border-radius: 6px;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 450;
  cursor: pointer;
  transition: background-color 0.15s, color 0.15s;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: var(--gray-10);
  color: var(--color-text);
}

.nav-item.active {
  background: var(--main-10);
  color: var(--main-700);
  font-weight: 600;
}

.nav-icon {
  flex-shrink: 0;
}

.nav-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Footer user area */
.sidebar-footer {
  border-top: 1px solid var(--gray-50);
  padding: 8px;
  flex-shrink: 0;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border-radius: 6px;
}

.user-section:hover {
  background: var(--gray-10);
}

.user-avatar {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--main-10);
  color: var(--main-700);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-role {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.user-menu-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
  flex-shrink: 0;
}

.user-menu-btn:hover {
  background: var(--gray-25);
  color: var(--color-text);
}

/* ========== Main Content ========== */
.main-content {
  flex: 1;
  overflow-y: auto;
  background: var(--gray-10);
}

/* Collapsed adjustments */
.collapsed .nav-section-title,
.collapsed .nav-divider {
  display: none;
}

.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}

.collapsed .sidebar-brand {
  justify-content: center;
  padding: 0;
}

.collapsed .brand-link {
  justify-content: center;
}

.collapsed .user-section {
  justify-content: center;
}

.collapsed .user-menu-btn {
  display: none;
}
</style>
