import { apiGet, apiSuperAdminGet, apiSuperAdminPost, apiSuperAdminPut, apiSuperAdminDelete } from './base'

export function getTagsGrouped() {
  return apiGet('/tags', {}, true)
}

export function listTags(params = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') q.append(k, v)
  })
  const qs = q.toString()
  return apiSuperAdminGet(`/tags${qs ? `?${qs}` : ''}`)
}

export function createTag(data) {
  return apiSuperAdminPost('/tags', data)
}

export function updateTag(id, data) {
  return apiSuperAdminPut(`/tags/${id}`, data)
}

export function deleteTag(id) {
  return apiSuperAdminDelete(`/tags/${id}`)
}
