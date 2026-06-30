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
 * 将后端错误响应解析为用户可读的 message。
 * 支持三种 detail 形态:
 *   1. Pydantic 422 校验错误的数组 [{type, loc, msg, input}, ...]
 *   2. 自定义 HTTPException(detail={...}) 的对象 {message, error}
 *   3. 最常见的 HTTPException(detail="string") 的字符串
 */
function formatErrorMessage(errorData, status, fallback) {
  if (!errorData) return fallback
  const detail = errorData.detail
  if (Array.isArray(detail)) {
    // Pydantic v2 422 标准结构
    const parts = detail.map((err) => {
      const field = Array.isArray(err?.loc) ? err.loc.filter((s) => s !== 'body').join('.') : ''
      return field ? `${field}: ${err.msg}` : err.msg
    })
    return parts.length ? parts.join('；') : fallback
  }
  if (detail && typeof detail === 'object') {
    return detail.message || detail.error || fallback
  }
  return detail || errorData.message || fallback
}

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
        errorMessage = formatErrorMessage(errorData, response.status, errorMessage)
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
        error.message = '权限不足'
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
      // 204 / 304 等无 body 响应,FastAPI 偶尔会带 Content-Type: application/json + 空 body,
      // response.json() 在空 body 时抛 SyntaxError: Unexpected end of JSON input.
      // 提前用状态码 + Content-Length 守卫,避免误读空 body。
      if (response.status === 204 || response.status === 304) {
        return null
      }
      const contentLength = response.headers.get('Content-Length')
      if (contentLength === '0') {
        return null
      }
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

/**
 * 把 query 对象拼接到 path 上,只忽略 null/undefined/空字符串。
 * - 数字 0 / 布尔 false 会被保留(后端可能用 0 做有意义的过滤值)
 * - 数组按 RFC-3986 重复键展开(?tag_ids=1&tag_ids=2);本项目目前未使用,但留扩展位
 * - 已带 ? 的 path 直接追加 &;否则用 ?
 */
function appendQuery(path, query) {
  if (!query || typeof query !== 'object') return path
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) {
      for (const item of v) {
        if (item === undefined || item === null || item === '') continue
        sp.append(k, String(item))
      }
    } else {
      sp.append(k, String(v))
    }
  }
  const qs = sp.toString()
  if (!qs) return path
  return path + (path.includes('?') ? '&' : '?') + qs
}

/**
 * apiGet — 第 2 个参数是查询参数对象(不是 fetch options)。
 * 历史上这里曾错把 query 当 fetch options 展开,导致所有 GET 查询参数被静默丢弃,
 * 现已统一改为 URLSearchParams 拼到 URL。
 */
export function apiGet(path, params = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(appendQuery(path, params), { method: 'GET' }, requiresAuth, responseType)
}

export function apiAdminGet(path, params = {}, responseType = 'json') {
  checkAdminPermission()
  return apiGet(`/admin${path}`, params, true, responseType)
}

export function apiSuperAdminGet(path, params = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiGet(`/admin${path}`, params, true, responseType)
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
  return apiPost(`/admin${path}`, data, options, true, responseType)
}

export function apiSuperAdminPost(path, data = {}, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiPost(`/admin${path}`, data, options, true, responseType)
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
  return apiPut(`/admin${path}`, data, options, true, responseType)
}

export function apiSuperAdminPut(path, data = {}, options = {}, responseType = 'json') {
  checkSuperAdminPermission()
  return apiPut(`/admin${path}`, data, options, true, responseType)
}

// ---------------------------------------------------------------------------
// DELETE
// ---------------------------------------------------------------------------
export function apiDelete(path, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(path, { method: 'DELETE', ...options }, requiresAuth, responseType)
}

export function apiAdminDelete(path, options = {}) {
  checkAdminPermission()
  return apiDelete(`/admin${path}`, options, true)
}

export function apiSuperAdminDelete(path, options = {}) {
  checkSuperAdminPermission()
  return apiDelete(`/admin${path}`, options, true)
}
