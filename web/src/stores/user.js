import { defineStore } from 'pinia'
import { message } from 'ant-design-vue'

/**
 * 当前登录用户状态。
 *
 * - token + user 通过 pinia-plugin-persistedstate 持久化到 localStorage
 * - 请求拦截器（apis/base.js）通过 getAuthHeaders() 注入 Authorization Header
 * - 401 响应时由 base.js 调用 logout() 并跳转登录页
 */
export const useUserStore = defineStore('user', {
  state: () => ({
    user: null, // { id, username, role: 'user' | 'admin' | 'super_admin' }
    token: null
  }),
  getters: {
    isLoggedIn: (s) => Boolean(s.token && s.user),
    isAdmin: (s) => s.user?.role === 'admin' || s.user?.role === 'super_admin',
    isSuperAdmin: (s) => s.user?.role === 'super_admin'
  },
  actions: {
    setSession({ user, token }) {
      this.user = user
      this.token = token
    },
    getAuthHeaders() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {}
    },
    logout() {
      this.user = null
      this.token = null
    }
  },
  persist: {
    pick: ['user', 'token']
  }
})

/**
 * 提前检查管理员权限 - 在调用 apiAdmin* 时使用。
 * 真正的权限边界在后端；前端只做"早期失败"以提升开发期可见度。
 */
export function checkAdminPermission() {
  const store = useUserStore()
  if (!store.isAdmin) {
    message.error('需要管理员权限')
    throw new Error('需要管理员权限')
  }
}

export function checkSuperAdminPermission() {
  const store = useUserStore()
  if (!store.isSuperAdmin) {
    message.error('需要超级管理员权限')
    throw new Error('需要超级管理员权限')
  }
}
