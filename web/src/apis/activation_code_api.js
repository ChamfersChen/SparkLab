import { apiSuperAdminGet, apiSuperAdminPost, apiSuperAdminPut, apiSuperAdminDelete } from './base'

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
  return apiSuperAdminGet(`/activation-codes${qs}`)
}

export function generateCodes(data) {
  return apiSuperAdminPost('/activation-codes/generate', data)
}

export function toggleCodeStatus(codeId) {
  return apiSuperAdminPut(`/activation-codes/${codeId}/toggle`)
}

export function updateCodeNote(codeId, data) {
  return apiSuperAdminPut(`/activation-codes/${codeId}/note`, data)
}

export function deleteCode(codeId) {
  return apiSuperAdminDelete(`/activation-codes/${codeId}`)
}
