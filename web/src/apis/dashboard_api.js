import { apiAdminGet } from './base'

/**
 * 数据看板 API（管理后台）
 *
 * 所有端点都接受 `range` 参数：'7d' | '30d' | 'all'，默认 'all'。
 * apiAdmin* 系列已自动拼 /admin 前缀，调用方无需再写。
 */

/**
 * 获取核心指标 + 趋势图数据。
 * @param {string} range - '7d' | '30d' | 'all'，默认 'all'
 */
export function getDashboardStats(range = 'all') {
  return apiAdminGet('/dashboard/stats', { range })
}

/**
 * 模板 Top N。
 * @param {string} range
 * @param {number} limit - 默认 10
 */
export function getTopTemplates(range = 'all', limit = 10) {
  return apiAdminGet('/dashboard/top-templates', { range, limit })
}

/**
 * 流程 Top N。
 * @param {string} range
 * @param {number} limit - 默认 10
 */
export function getTopPlaybooks(range = 'all', limit = 10) {
  return apiAdminGet('/dashboard/top-playbooks', { range, limit })
}

/**
 * 近期发布动态。
 * @param {number} limit - 默认 20
 */
export function getRecentActivity(limit = 20) {
  return apiAdminGet('/dashboard/recent-activity', { limit })
}
