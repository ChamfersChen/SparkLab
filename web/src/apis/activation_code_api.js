import { apiSuperAdminGet, apiSuperAdminPost, apiSuperAdminPut } from './base'

function buildQuery(params) {
  const q = new URLSearchParams()
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.append(k, v)
  })
  const s = q.toString()
  return s ? `?${s}` : ''
}

export function listActivationCodes(params = {}) {
  const qs = buildQuery(params)
  return apiSuperAdminGet(`/admin/activation-codes${qs}`)
}

export function generateCodes(data) {
  return apiSuperAdminPost('/admin/activation-codes/generate', data)
}

export function toggleCodeStatus(codeId) {
  return apiSuperAdminPut(`/admin/activation-codes/${codeId}/toggle`)
}

export function updateCodeNote(codeId, data) {
  return apiSuperAdminPut(`/admin/activation-codes/${codeId}/note`, data)
}
