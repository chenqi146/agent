import request from './request'
import routesConfig from '@/router/routes.json'
import { appTag } from './constants'

const apiRoutes = routesConfig.api.agent.rag.kb

export const ragApi = {
  /**
   * 创建知识库
   * @param {Object} data - KnowledgeBaseCreateRequest
   * @returns {Promise} - ApiResponse
   */
  createKnowledgeBase(data) {
    return request.post(apiRoutes.create, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 更新知识库
   * @param {Object} data - KnowledgeBaseUpdateRequest
   * @returns {Promise} - ApiResponse
   */
  updateKnowledgeBase(data) {
    return request.post(apiRoutes.update, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 获取知识库详情
   * @param {Object} data - KnowledgeBaseIdRequest
   * @returns {Promise} - ApiResponse
   */
  getKnowledgeBaseDetail(data) {
    return request.post(apiRoutes.detail, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 删除知识库
   * @param {Object} data - KnowledgeBaseIdRequest
   * @returns {Promise} - ApiResponse
   */
  deleteKnowledgeBase(data) {
    return request.post(apiRoutes.delete, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 导出知识库（返回知识库及文件列表的 JSON 数据）
   * @param {Object} data - KnowledgeBaseIdRequest
   * @returns {Promise} - ApiResponse
   */
  exportKnowledgeBase(data) {
    return request.post(apiRoutes.export, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 获取知识库列表
   * @param {Object} params - 请求参数（包含分页信息）
   * @returns {Promise} - ApiResponse
   */
  getKnowledgeBaseList(params) {
    return request.post(apiRoutes.list, {
      tag: appTag,
      timestamp: Date.now(),
      data: params
    })
  },

  /**
   * 获取知识库名称列表
   * @returns {Promise} - ApiResponse
   */
  getKnowledgeBaseNameList() {
    return request.post(apiRoutes.namelist, {
      tag: appTag,
      timestamp: Date.now(),
      data: {}
    })
  },

  /**
   * 上传文件（FormData方式）
   * @param {FormData} formData - 包含文件的FormData对象
   * @param {Object} onUploadProgress - 上传进度回调
   * @returns {Promise} - ApiResponse { data: { filename: string } }
   */
  uploadFile(formData, onUploadProgress) {
    // 大文件上传放宽超时（10 分钟），避免 40MB+ 文件被全局 30s 超时截断
    return request.post(apiRoutes.file.upload, formData, {
      timeout: 600000,
      onUploadProgress: (progressEvent) => {
        if (onUploadProgress) {
          const loaded = progressEvent.loaded != null ? Number(progressEvent.loaded) : 0
          const total = progressEvent.total != null && progressEvent.total > 0 ? Number(progressEvent.total) : 1
          const progress = Math.min(100, Math.max(0, Math.round((loaded * 100) / total)))
          onUploadProgress(Number.isFinite(progress) ? progress : 0)
        }
      }
    })
  },

  /**
   * 处理文件（携带文件名、文件信息、控制指令）
   * @param {Object} data - 文件处理请求
   * @param {string} data.filename - 文件名
   * @param {Object} data.fileInfo - 文件信息（大小、字符数等）
   * @param {string} data.command - 控制指令
   * @param {string} data.kbId - 知识库ID（可选）
   * @returns {Promise} - ApiResponse
   */
  processFile(data) {
    // 处理请求可能略慢，使用 2 分钟超时
    return request.post(apiRoutes.file.process, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    }, { timeout: 120000 })
  },

  /**
   * 查询文件处理状态
   * @param {Object} data - 文件状态查询请求
   * @param {string} data.file_id - 文件ID
   * @param {string} data.kb_id - 知识库ID
   * @returns {Promise} - ApiResponse { data: { file_id, kb_id, processing_status, embedding_status, embedding_progress, error_message } }
   */
  checkFileStatus(data) {
    return request.post(apiRoutes.file.status, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    }, { timeout: 90000 })
  },

  /**
   * 更新文件启用状态
   * @param {Object} data - { kb_id, file_id, status }
   * @returns {Promise} - ApiResponse
   */
  updateFileStatus(data) {
    return request.post(apiRoutes.file.updateStatus, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 删除知识库中的单个文件
   * @param {Object} data - { kb_id, file_id }
   * @returns {Promise} - ApiResponse
   */
  deleteFile(data) {
    return request.post(apiRoutes.file.delete, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 获取单个文件的下载链接
   * @param {Object} data - { kb_id, file_id }
   * @returns {Promise} - ApiResponse { data: { url, file_name } }
   */
  getFileDownloadUrl(data) {
    return request.post(apiRoutes.file.download, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 获取本体Schema（标签和关系类型）
   * @returns {Promise} - ApiResponse
   */
  getOntologySchema() {
    return request.get(apiRoutes.ontology.schema, {
      params: {
        tag: appTag,
        timestamp: Date.now()
      }
    })
  },

  /**
   * 获取本体节点列表
   * @param {Object} params - 查询参数
   * @returns {Promise} - ApiResponse
   */
  getOntologyNodes(params) {
    return request.post(apiRoutes.ontology.nodes, {
      tag: appTag,
      timestamp: Date.now(),
      data: params
    })
  },

  /**
   * 创建本体节点
   * @param {Object} data - OntologyNodeCreateRequest
   * @returns {Promise} - ApiResponse
   */
  createOntologyNode(data) {
    return request.post(apiRoutes.ontology.create, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 更新本体节点
   * @param {Object} data - OntologyNodeUpdateRequest
   * @returns {Promise} - ApiResponse
   */
  updateOntologyNode(data) {
    return request.post(apiRoutes.ontology.update, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 删除本体节点
   * @param {Object} data - OntologyNodeDeleteRequest
   * @returns {Promise} - ApiResponse
   */
  deleteOntologyNode(data) {
    return request.post(apiRoutes.ontology.delete, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 获取本体统计信息
   * @returns {Promise} - ApiResponse
   */
  getOntologyStatistics() {
    return request.get(apiRoutes.ontology.statistics, {
      params: {
        tag: appTag,
        timestamp: Date.now()
      }
    })
  },

  /**
   * 查询知识库下的知识信息列表
   * @param {Object} data - { kb_id }
   * @returns {Promise} - ApiResponse { data: { items: [] } }
   */
  getKnowledgeList(data) {
    return request.post(apiRoutes.knowledgeList, {
      tag: appTag,
      timestamp: Date.now(),
      data: data
    })
  },

  /**
   * 创建知识片段
   * @param {Object} data - KnowledgeSegmentCreateRequest { file_id, content, status, title }
   * @returns {Promise} - ApiResponse { id: int }
   */
  createKnowledgeSegment(data) {
    return request.post('/v1/agent/rag/kb/segment/create', {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },

  /**
   * 查询指定文件下的知识片段列表
   * @param {Object} data - KnowledgeSegmentListRequest { file_id, page_no, page_size, status }
   * @returns {Promise} - ApiResponse { data: { items: [] } }
   */
  getKnowledgeSegments(data) {
    return request.post('/v1/agent/rag/kb/segment/list', {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },

  /**
   * 更新知识片段
   * @param {Object} data - KnowledgeSegmentUpdateRequest { id, content, status, title }
   * @returns {Promise} - ApiResponse
   */
  updateKnowledgeSegment(data) {
    return request.post('/v1/agent/rag/kb/segment/update', {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },

  /**
   * 删除知识片段
   * @param {Object} data - KnowledgeSegmentIdRequest { id }
   * @returns {Promise} - ApiResponse
   */
  deleteKnowledgeSegment(data) {
    return request.post('/v1/agent/rag/kb/segment/delete', {
      tag: appTag,
      timestamp: Date.now(),
      data
    })
  },


}
