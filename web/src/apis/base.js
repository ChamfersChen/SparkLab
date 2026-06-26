import { message } from 'ant-design-vue'
import { useUserStore, checkAdminPermission, checkSuperAdminPermission } from '@/stores/user'

/**
 * SparkLab 基础 API 请求封装（基于 Yuxi base.js 微调）
 *
 * 鉴权方式：JWT Token + Authorization: Bearer Header（与 Yuxi 一致）
 *   - Token 由 user store 管理，登录成功后写入 localStorage
 *   - 每次请求由 userStore.getAuthHeaders() 注入 Header
 *   - 401 时清空本地 token 并跳转登录页
 *
 * 调用方写相对路径（如 '/templates'），由本模块统一拼接 '/api' 前缀。
 */

const BASE = '/api'

/**
 * 发送 API 请求的基础函数
 * @param {string} path - API 端点（不含 /api 前缀）
 * @param {Object} options - 请求选项
 * @param {boolean} requiresAuth - 是否需要认证头
 * @param {string} responseType - 响应类型: 'json' | 'text' | 'blob'
 */
export async function apiRequest(path, options = {}, requiresAuth = true, responseType = 'json') {
  try {
    const isFormData = options?.body instanceof FormData
    const requestOptions = {
      ...options,
      headers: {
        ...(!isFormData ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers
      }
    }

    if (requiresAuth) {
      const userStore = useUserStore()
      if (!userStore.isLoggedIn) {
        throw new Error('用户未登录')
      }
      Object.assign(requestOptions.headers, userStore.getAuthHeaders())
    }

    const response = await fetch(BASE + path, requestOptions)

    if (!response.ok) {
      let errorMessage = `请求失败: ${response.status}, ${response.statusText}`
      let errorData = null

      try {
        errorData = await response.json()
        const detail = errorData.detail
        if (detail && typeof detail === 'object') {
          errorMessage = detail.message || detail.error || errorMessage
        } else {
          errorMessage = detail || errorData.message || errorMessage
        }
      } catch {
        // 非 JSON 响应
      }

      const error = new Error(errorMessage)
      error.response = {
        status: response.status,
        statusText: response.statusText,
        data: errorData
      }

      if (response.status === 401) {
        const userStore = useUserStore()
        const isTokenExpired =
          errorMessage?.includes('令牌已过期') || errorMessage?.includes('token expired')

        message.error(isTokenExpired ? '登录已过期，请重新登录' : '认证失败，请重新登录')

        if (userStore.isLoggedIn) {
          userStore.logout()
        }

        setTimeout(() => {
          window.location.href = '/login'
        }, 1500)
        throw error
      } else if (response.status === 403) {
        error.message = '没有权限执行此操作'
        throw error
      } else if (response.status === 500) {
        error.message = '服务器内部错误，请使用 docker logs sparklab-api-dev 查看详细日志'
        throw error
      }

      throw error
    }

    // 根据 responseType 处理响应
    if (responseType === 'blob') {
      return response
    } else if (responseType === 'json') {
      const contentType = response.headers.get('Content-Type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }
      return await response.text()
    } else if (responseType === 'text') {
      return await response.text()
    } else {
      return response
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('API 请求错误:', error)
    }
    throw error
  }
}

// ---------------------------------------------------------------------------
// GET
// ---------------------------------------------------------------------------
export function apiGet(path, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(path, { method: 'GET', ...options }, requiresAuth, responseType)
}

export function apiAdminGet(path, options = {}, responseType = 'json') {
  checkAdminPermission()
  return apiGet(path, options, true, responseType)
}

export function apiSuperAdminGet(path, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiGet(path, options, true, responseType)
}

// ---------------------------------------------------------------------------
// POST
// ---------------------------------------------------------------------------
export function apiPost(path, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(
    path,
    {
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data),
      ...options
    },
    requiresAuth,
    responseType
  )
}

export function apiAdminPost(path, data = {}, options = {}, responseType = 'json') {
  checkAdminPermission()
  return apiPost(path, data, options, true, responseType)
}

export function apiSuperAdminPost(path, data = {}, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiPost(path, data, options, true, responseType)
}

// ---------------------------------------------------------------------------
// PUT
// ---------------------------------------------------------------------------
export function apiPut(path, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(
    path,
    {
      method: 'PUT',
      body: data instanceof FormData ? data : JSON.stringify(data),
      ...options
    },
    requiresAuth,
    responseType
  )
}

export function apiAdminPut(path, data = {}, options = {}, responseType = 'json') {
  checkAdminPermission()
  return apiPut(path, data, options, true, responseType)
}

export function apiSuperAdminPut(path, data = {}, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiPut(path, data, options, true, responseType)
}

// ---------------------------------------------------------------------------
// DELETE
// ---------------------------------------------------------------------------
export function apiDelete(path, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(path, { method: 'DELETE', ...options }, requiresAuth, responseType)
}

export function apiAdminDelete(path, options = {}) {
  checkAdminPermission()
  return apiDelete(path, options, true)
}

export function apiSuperAdminDelete(path, options = {}) {
  checkSuperAdminPermission()
  return apiDelete(path, options, true)
}
