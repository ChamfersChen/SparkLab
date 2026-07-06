import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, layout: 'blank' }
  },
  {
    path: '/activate',
    name: 'activate',
    component: () => import('@/views/ActivateView.vue'),
    meta: { public: true, layout: 'blank' }
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { public: true, layout: 'blank' }
  },
  {
    path: '/admin/activation-codes',
    name: 'admin-activation-codes',
    component: () => import('@/views/admin/ActivationCodeManage.vue'),
    meta: { title: '激活码管理', layout: 'app' }
  },
  {
    path: '/admin/admins',
    name: 'admin-admins',
    component: () => import('@/views/admin/AdminAccountManage.vue'),
    meta: { title: '管理员账号', layout: 'app' }
  },
  {
    path: '/admin/tags',
    name: 'admin-tags',
    component: () => import('@/views/admin/TagManage.vue'),
    meta: { title: '标签管理', layout: 'app' }
  },
  {
    path: '/templates',
    name: 'templates',
    component: () => import('@/views/templates/TemplateList.vue'),
    meta: { title: '模板库', layout: 'app' }
  },
  {
    path: '/templates/:id',
    name: 'template-detail',
    component: () => import('@/views/templates/TemplateDetail.vue'),
    meta: { title: '模板详情', layout: 'app' }
  },
  {
    path: '/templates/:id/fill',
    name: 'template-fill',
    component: () => import('@/views/templates/TemplateFill.vue'),
    meta: { title: '生成提示词', layout: 'app' }
  },
  {
    path: '/admin/templates',
    name: 'admin-templates',
    component: () => import('@/views/admin/TemplateManage.vue'),
    meta: { title: '模板管理', layout: 'app' }
  },
  {
    path: '/admin/templates/create',
    name: 'admin-template-create',
    component: () => import('@/views/admin/TemplateEditor.vue'),
    meta: { title: '新建模板', layout: 'app' }
  },
  {
    path: '/admin/dashboard',
    name: 'admin-dashboard',
    component: () => import('@/views/admin/AdminDashboardView.vue'),
    meta: { title: '数据看板', layout: 'app' }
  },
  {
    path: '/admin/templates/:id/edit',
    name: 'admin-template-edit',
    component: () => import('@/views/admin/TemplateEditor.vue'),
    meta: { title: '编辑模板', layout: 'app' }
  },
  {
    path: '/playbooks',
    name: 'playbooks',
    component: () => import('@/views/playbooks/PlaybookList.vue'),
    meta: { title: '流程库', layout: 'app' }
  },
  {
    path: '/playbooks/:id',
    name: 'playbook-run',
    component: () => import('@/views/playbooks/PlaybookRun.vue'),
    meta: { title: '流程运行', layout: 'app' }
  },
  {
    path: '/admin/playbooks',
    name: 'admin-playbooks',
    component: () => import('@/views/admin/PlaybookManage.vue'),
    meta: { title: '流程管理', layout: 'app' }
  },
  {
    path: '/admin/playbooks/create',
    name: 'admin-playbook-create',
    component: () => import('@/views/admin/PlaybookEditor.vue'),
    meta: { title: '新建流程', layout: 'app' }
  },
  {
    path: '/admin/playbooks/:id/edit',
    name: 'admin-playbook-edit',
    component: () => import('@/views/admin/PlaybookEditor.vue'),
    meta: { title: '编辑流程', layout: 'app' }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { title: '个人中心', layout: 'app' }
  },
  {
    path: '/favorites',
    name: 'favorites',
    component: () => import('@/views/FavoritesView.vue'),
    meta: { title: '我的收藏', layout: 'app' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true, layout: 'blank' }
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
