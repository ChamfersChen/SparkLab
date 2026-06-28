
import { apiSuperAdminGet, apiSuperAdminPost, apiSuperAdminPut, apiSuperAdminDelete } from './base'

function buildQuery(params) {
  const q = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.append(k, v)
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

// ========== 管理员账号管理 ==========

export function listAdminUsers(params = {}) {
  const qs = buildQuery(params)
  return apiSuperAdminGet(`/admin/admins${qs}`)
}

export function updateUserRole(userId, role) {
  return apiSuperAdminPut(`/admin/admins/${userId}/role`, { role })
}

export function toggleUserActive(userId) {
  return apiSuperAdminPut(`/admin/admins/${userId}/toggle`)
}

export function deleteUser(userId) {
  return apiSuperAdminDelete(`/admin/admins/${userId}`)
}

// ========== 管理员激活码管理 ==========

export function listAdminCodes(params = {}) {
  const qs = buildQuery(params)
  return apiSuperAdminGet(`/admin/admins/codes${qs}`)
}

export function generateAdminCodes(data) {
  return apiSuperAdminPost('/admin/admins/codes/generate', data)
}

export function toggleAdminCodeStatus(codeId) {
  return apiSuperAdminPut(`/admin/admins/codes/${codeId}/toggle`)
}

export function deleteAdminCode(codeId) {
  return apiSuperAdminDelete(`/admin/admins/codes/${codeId}`)
}

