import { apiGet, apiPost, apiDelete } from './base'

/**
 * 工作流运行记录 API (个人中心 / 我的运行记录).
 *
 * 命名约定: 用户端不带前缀, 路径以 /playbooks/runs 为基础.
 * 资源属于当前登录用户, 后端按 user_id 隔离.
 */

export function listPlaybookRuns(params = {}) {
  return apiGet('/playbooks/runs', params)
}

export function getPlaybookRun(id) {
  return apiGet(`/playbooks/runs/${id}`)
}

export function createPlaybookRun(data) {
  return apiPost('/playbooks/runs', data)
}

export function deletePlaybookRun(id) {
  return apiDelete(`/playbooks/runs/${id}`)
}
