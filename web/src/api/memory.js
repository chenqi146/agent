import request from './request'
import routesConfig from '@/router/routes.json'
import { appTag } from './constants'

const memoryRoute = routesConfig.api.agent.memory
const memoryContentRoutes = routesConfig.api.agent.memoryContent

export const memoryApi = {
  /**
   * 获取当前智能体的记忆配置
   * @returns {Promise} - ApiResponse { data: { ...config } }
   */
  getConfig() {
    return request.get(memoryRoute, {
      params: {
        // 可按需扩展
      }
    })
  },

  /**
   * 保存记忆配置
   * @param {Object} data - 记忆配置对象
   * @returns {Promise} - ApiResponse
   */
  saveConfig(data) {
    return request.post(memoryRoute, {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },

  /**
   * 查询记忆内容列表
   * @param {Object} params - 查询条件 { timeRange, category, roleType, keyword, page, pageSize }
   * @returns {Promise} - ApiResponse { data: { total, items: [] } }
   */
  searchContent(params) {
    return request.post(memoryContentRoutes.search, {
      tag: appTag,
      timestamp: Date.now(),
      data: params
    })
  },

  /**
   * 批量删除记忆
   * @param {Array<string>} ids - 待删除的记忆ID列表
   * @returns {Promise} - ApiResponse
   */
  deleteContent(ids) {
    return request.post(memoryContentRoutes.delete, {
      tag: appTag,
      timestamp: Date.now(),
      data: { ids }
    })
  },

  /**
   * 清空当前智能体的所有记忆
   * @returns {Promise} - ApiResponse
   */
  clearContent() {
    return request.post(memoryContentRoutes.clear, {
      tag: appTag,
      timestamp: Date.now(),
      data: {}
    })
  }
}
