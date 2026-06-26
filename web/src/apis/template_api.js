import { apiGet, apiPost, apiAdminGet, apiAdminPost, apiAdminPut, apiAdminDelete } from './base'

/**
 * 用户端模板 API
 */
export function listTemplates(params = {}) {
  return apiGet('/templates', params)
}

export function getTemplate(id) {
  return apiGet(`/templates/${id}`)
}

export function getFillData(id) {
  return apiGet(`/templates/${id}/fill`)
}

export function incrementUseCount(id) {
  return apiPost(`/templates/${id}/use`)
}

/**
 * 管理后台模板 API
 *
 * 注意：apiAdmin* 系列不会自动加 /admin 前缀，需在 path 中显式写出。
 */
export function adminListTemplates(params = {}) {
  return apiAdminGet('/admin/templates', params)
}

export function adminGetTemplate(id) {
  return apiAdminGet(`/admin/templates/${id}`)
}

export function adminCreateTemplate(data) {
  return apiAdminPost('/admin/templates', data)
}

export function adminUpdateTemplate(id, data) {
  return apiAdminPut(`/admin/templates/${id}`, data)
}

export function adminChangeStatus(id, status) {
  return apiAdminPut(`/admin/templates/${id}/status`, { status })
}

export function adminDeleteTemplate(id) {
  return apiAdminDelete(`/admin/templates/${id}`)
}
