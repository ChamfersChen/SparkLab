import { apiPost, apiGet, apiPut } from './base'

export function login(data) {
  return apiPost('/auth/login', data, {}, false)
}

export function logout() {
  return apiPost('/auth/logout', {}, {})
}

export function getCurrentUser() {
  return apiGet('/auth/me')
}

export function changePassword(data) {
  return apiPut('/auth/password', data)
}

export function verifyActivationCode(code) {
  return apiPost('/activation/verify', { code }, {}, false)
}

export function activate(data) {
  return apiPost('/activation/activate', data, {}, false)
}
