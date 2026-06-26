import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/activate',
    name: 'activate',
    component: () => import('@/views/ActivateView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    // 公开页：未登录用户也能看到欢迎页与产品介绍；
    // Hero 区按钮根据登录态切换（登录 ↔ 进入系统）。
    meta: { public: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局守卫：未登录访问非公开页面 → 跳登录
router.beforeEach((to) => {
  const userStore = useUserStore()
  if (!to.meta?.public && !userStore.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
