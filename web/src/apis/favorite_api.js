import { apiGet, apiPost, apiDelete } from './base'

/**
 * 收藏 API
 *
 * Toggle 模式: POST /favorites 切换收藏状态 (已收藏→取消, 未收藏→添加)
 */

/** 获取当前用户收藏列表 */
export function getFavorites(params = {}) {
  return apiGet('/favorites', params)
}

/** 切换收藏状态 (toggle) */
export function toggleFavorite(targetType, targetId) {
  return apiPost('/favorites', { target_type: targetType, target_id: targetId })
}

/** 取消收藏 */
export function removeFavorite(targetType, targetId) {
  return apiDelete(`/favorites/${targetType}/${targetId}`)
}

/** 查询是否已收藏 */
export function checkFavorited(targetType, targetId) {
  return apiGet('/favorites/check', { type: targetType, id: targetId })
}
