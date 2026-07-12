import { apiGet, apiPost, apiPut, apiDelete, apiAdminGet, apiAdminPost, apiAdminPut, apiAdminDelete, apiSuperAdminDelete } from './base'

/**
 * 流程 API。
 *
 * 命名约定:用户端不带前缀(playbook),管理端带 admin 前缀(adminPlaybook),我的流程带 my 前缀。
 * 路径以 /playbooks 为基础。
 */

/* ---------------- 用户端 ---------------- */
export function listPlaybooks(params = {}) {
  return apiGet('/playbooks', params)
}
export function getPlaybook(id) {
  return apiGet(`/playbooks/${id}`)
}
export function incrementUseCount(id) {
  return apiPost(`/playbooks/${id}/use`)
}
export function runPlaybook(id, data) {
  return apiPost(`/playbooks/${id}/run`, data)
}

/* ---------------- 我的流程（普通用户管理自己创建的） ---------------- */
export function myListPlaybooks(params = {}) {
  return apiGet('/my/playbooks', params)
}
export function myGetPlaybook(id) {
  return apiGet(`/my/playbooks/${id}`)
}
export function myCreatePlaybook(data) {
  return apiPost('/my/playbooks', data)
}
export function myUpdatePlaybook(id, data) {
  return apiPut(`/my/playbooks/${id}`, data)
}
export function myDeletePlaybook(id) {
  return apiDelete(`/my/playbooks/${id}`)
}

/* ---------------- 管理后台 ---------------- */
export function adminListPlaybooks(params = {}) {
  return apiAdminGet('/playbooks', params)
}
export function adminGetPlaybook(id) {
  return apiAdminGet(`/playbooks/${id}`)
}
export function adminCreatePlaybook(data) {
  return apiAdminPost('/playbooks', data)
}
export function adminUpdatePlaybook(id, data) {
  return apiAdminPut(`/playbooks/${id}`, data)
}
export function adminChangeStatus(id, status) {
  return apiAdminPut(`/playbooks/${id}/status`, { status })
}
export function adminDeletePlaybook(id) {
  return apiAdminDelete(`/playbooks/${id}`)
}
export function adminHardDeletePlaybook(id) {
  return apiSuperAdminDelete(`/playbooks/${id}/hard`)
}
