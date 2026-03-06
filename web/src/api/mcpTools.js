import request from './request'
import routesConfig from '@/router/routes.json'
import { appTag } from './constants'

const apiRoutes = routesConfig.api.agent.mcptools

export const mcpToolsApi = {
  // --- Tool Integration & Management ---
  getToolList(params) {
    return request.get(apiRoutes.integrate.list, {
      params: {
        tag: appTag,
        timestamp: Date.now(),
        ...params
      }
    })
  },
  addTool(data) {
    return request.post(apiRoutes.integrate.add, {
      tag: appTag,
      timestamp: Date.now(),
      ...data
    })
  },
  updateTool(data) {
    return request.post(apiRoutes.integrate.update, {
      tag: appTag,
      timestamp: Date.now(),
      ...data
    })
  },
  deleteTool(id) {
    return request.post(apiRoutes.integrate.delete, {
      tag: appTag,
      timestamp: Date.now(),
      tool_id: id
    })
  },
  discoverTools(url, apiKey) {
    return request.get(apiRoutes.integrate.discover, {
      params: {
        tag: appTag,
        timestamp: Date.now(),
        url: url,
        api_key: apiKey
      }
    })
  },

  // --- MCP Tool Logs ---
  getToolLogs(params) {
    return request.post(apiRoutes.log.list, {
      tag: appTag,
      timestamp: Date.now(),
      ...params
    })
  },

  // --- Tool Rating ---
  getToolRatingList(params) {
    return request.get(apiRoutes.rating.list, {
      params: {
        tag: appTag,
        timestamp: Date.now(),
        ...params
      }
    })
  },
  addToolRating(data) {
    return request.post(apiRoutes.rating.add, {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },

  // --- Tool Relationships ---
  getToolRelations(params) {
    return request.get(apiRoutes.relation.list, {
      params: {
        tag: appTag,
        timestamp: Date.now(),
        ...params
      }
    })
  },
  addToolRelation(data) {
    return request.post(apiRoutes.relation.add, {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },

  // --- Snapshot Version Management ---
  getVersionList(params) {
    return request.get(apiRoutes.version.list, {
      params: {
        tag: appTag,
        timestamp: Date.now(),
        ...params
      }
    })
  },
  createVersion(data) {
    return request.post(apiRoutes.version.create, {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },
  
  // --- MCP Server Management ---
  getServerList(params) {
    return request.get(apiRoutes.server.list, {
      params: {
        tag: appTag,
        timestamp: Date.now(),
        ...params
      }
    })
  },
  addServer(data) {
    return request.post(apiRoutes.server.add, {
      tag: appTag,
      timestamp: Date.now(),
      ...data
    })
  },

  restoreVersion(id) {

    return request.post(apiRoutes.version.restore, {
      tag: appTag,
      timestamp: Date.now(),
      data: { id }
    })
  },

  // --- Tool Discovery Model ---
  searchTools(params) {
    return request.post(apiRoutes.discovery.search, {
      tag: appTag,
      timestamp: Date.now(),
      data: params
    })
  }
}
