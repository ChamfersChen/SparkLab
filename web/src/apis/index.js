/**
 * API 模块索引文件 - 统一导出所有 API 方法。
 *
 * 阶段 2 骨架仅暴露 base 工具函数；后续业务模块（auth_api / template_api ...）
 * 加入时在此处补 `export * from './xxx_api'`。
 */

export {
  apiRequest,
  apiGet,
  apiPost,
  apiPut,
  apiDelete,
  apiAdminGet,
  apiAdminPost,
  apiAdminPut,
  apiAdminDelete,
  apiSuperAdminGet,
  apiSuperAdminPost,
  apiSuperAdminPut,
  apiSuperAdminDelete
} from './base'
