import request from './request'
import routesConfig from '@/router/routes.json'

const apiRoutes = routesConfig.api.prompt

function wrap(data) {
  return {
    tag: 'web',
    timestamp: Date.now(),
    data
  }
}

export const promptApi = {
  /**
   * List prompt templates
   * @param {Object} params - { page, size, keyword, status }
   */
  list(params) {
    return request.post(apiRoutes.list, wrap(params))
  },

  /**
   * Get template detail
   * @param {number} id 
   */
  getDetail(id) {
    return request.post(apiRoutes.detail, wrap({ id }))
  },

  /**
   * Create new template
   * @param {Object} data 
   */
  create(data) {
    return request.post(apiRoutes.save, wrap(data))
  },

  /**
   * Update template
   * @param {Object} data 
   */
  update(data) {
    return request.post(apiRoutes.update, wrap(data))
  },

  /**
   * Delete template
   * @param {number} id 
   */
  delete(id) {
    return request.post(apiRoutes.delete, wrap({ id }))
  },

  /**
   * Toggle template status
   * @param {number} id 
   * @param {string} status - 'enabled' | 'draft'
   */
  toggleStatus(id, status) {
    return request.post(apiRoutes.status, wrap({ id, status }))
  },

  /**
   * Run A/B Test
   * @param {Object} data 
   */
  runAbTest(data) {
    return request.post(apiRoutes.test.ab, wrap(data))
  },

  /**
   * Run Quick Test
   * @param {Object} data 
   */
  runQuickTest(data) {
    return request.post(apiRoutes.test.quick, wrap(data))
  },

  /**
   * Run Batch Test
   * @param {Object} data 
   */
  runBatchTest(data) {
    return request.post(apiRoutes.test.batch, wrap(data))
  },

  /**
   * Generate prompt template
   * @param {Object} data - { systemPrompt, category }
   */
  generate(data) {
    return request.post(apiRoutes.generate, wrap(data))
  }
}
