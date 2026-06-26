import { apiGet, apiPost, apiPut, apiDelete, apiAdminGet, apiAdminPost, apiAdminPut, apiAdminDelete } from './base'

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
 */
export function adminListTemplates(params = {}) {
  return apiAdminGet('/templates', params)
}

export function adminGetTemplate(id) {
  return apiAdminGet(`/templates/${id}`)
}

export function adminCreateTemplate(data) {
  return apiAdminPost('/templates', data)
}

export function adminUpdateTemplate(id, data) {
  return apiAdminPut(`/templates/${id}`, data)
}

export function adminChangeStatus(id, status) {
  return apiAdminPut(`/templates/${id}/status`, { status })
}

export function adminDeleteTemplate(id) {
  return apiAdminDelete(`/templates/${id}`)
}
