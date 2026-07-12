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
 * 我的模板 API（普通用户管理自己创建的模板）
 */
export function myListTemplates(params = {}) {
  return apiGet('/my/templates', params)
}

export function myGetTemplate(id) {
  return apiGet(`/my/templates/${id}`)
}

export function myCreateTemplate(data) {
  return apiPost('/my/templates', data)
}

export function myUpdateTemplate(id, data) {
  return apiPut(`/my/templates/${id}`, data)
}

export function myDeleteTemplate(id) {
  return apiDelete(`/my/templates/${id}`)
}

/**
 * 管理后台模板 API
 *
 * apiAdmin* 系列已自动拼 /admin 前缀，调用方无需再写。
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

/** 物理删除模板(仅超管) - 从 DB 移除记录,不可恢复。 */
export function adminHardDeleteTemplate(id) {
  return apiAdminDelete(`/templates/${id}/hard`)
}
