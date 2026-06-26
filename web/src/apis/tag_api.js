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
  return apiSuperAdminGet(`/admin/tags${qs ? `?${qs}` : ''}`)
}

export function createTag(data) {
  return apiSuperAdminPost('/admin/tags', data)
}

export function updateTag(id, data) {
  return apiSuperAdminPut(`/admin/tags/${id}`, data)
}

export function deleteTag(id) {
  return apiSuperAdminDelete(`/admin/tags/${id}`)
}
