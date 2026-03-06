import request from './request'
import routesConfig from '@/router/routes.json'

const apiRoutes = routesConfig.api.role

function wrap(data) {
  return {
    tag: 'web',
    timestamp: Date.now(),
    data
  }
}

export const roleApi = {
  /**
   * List application roles
   * @param {Object} params - { page, size, keyword, status }
   */
  list(params) {
    return request.post(apiRoutes.list, wrap(params))
  },

  /**
   * Get role detail
   * @param {number} id 
   */
  getDetail(id) {
    return request.post(apiRoutes.detail, wrap({ id }))
  },

  /**
   * Create new role
   * @param {Object} data 
   */
  create(data) {
    return request.post(apiRoutes.create, wrap(data))
  },

  /**
   * Update role
   * @param {Object} data 
   */
  update(data) {
    return request.post(apiRoutes.update, wrap(data))
  },

  /**
   * Delete role
   * @param {number} id 
   */
  delete(id) {
    return request.post(apiRoutes.delete, wrap({ id }))
  },

  /**
   * Toggle role status
   * @param {number} id 
   * @param {boolean} enabled 
   */
  toggleStatus(id, enabled) {
    return request.post(apiRoutes.status, wrap({ id, enabled }))
  }
}
