import { apiGet, apiPost, apiDelete } from './base'

/**
 * 模板使用记录 API (个人中心 / 我的模板使用记录).
 *
 * 资源属于当前登录用户, 后端按 user_id 隔离.
 */

export function listTemplateRuns(params = {}) {
  return apiGet('/templates/runs', params)
}

export function getTemplateRun(id) {
  return apiGet(`/templates/runs/${id}`)
}

export function createTemplateRun(data) {
  return apiPost('/templates/runs', data)
}

export function deleteTemplateRun(id) {
  return apiDelete(`/templates/runs/${id}`)
}
