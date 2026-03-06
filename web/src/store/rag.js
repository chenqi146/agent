import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ragApi } from '@/api/rag'
import { useAuthStore } from '@/store/auth'

// 知识库类型枚举
export const KB_TYPES = {
  document: 'document',
  vector: 'vector'
}

// 知识库状态枚举
export const KB_STATUS = {
  enabled: 'enabled',
  disabled: 'disabled',
  generating: 'generating'
}

export const useRagStore = defineStore('rag', () => {
  // 状态定义
  const knowledgeBases = ref([])
  const loading = ref(false)
  const error = ref(null)

  // 分页相关状态
  const pagination = ref({
    page: 1,
    pageSize: 10,
    total: 0
  })

  // 全局知识库名称列表（用于创建时选择）
  const kbNames = ref([])

  // 当前选中的知识库
  const currentKb = ref(null)

  // 文件上传相关状态
  const uploadingFiles = ref([])
  const uploadProgress = ref({})
  const uploadQueue = ref([])
  const isUploading = ref(false)

  // 计算属性
  const kbList = computed(() => knowledgeBases.value)
  const isLoading = computed(() => loading.value)
  const hasError = computed(() => !!error.value)
  const errorMessage = computed(() => error.value)

  // 获取知识库列表（支持分页）
  async function fetchKnowledgeBases(params = {}) {
    loading.value = true
    error.value = null

    try {
      const authStore = useAuthStore()
      // 合并分页参数
      const requestParams = {
        page_no: pagination.value.page,
        page_size: pagination.value.pageSize,
        keyword: params.keyword || '',
        ...params
      }

      console.log('📊 [RAG] 请求参数:', requestParams)
      const response = await ragApi.getKnowledgeBaseList(requestParams)
      console.log('📊 [RAG] 响应数据:', response)
      const { items = [], total = 0 } = response.data?.data || {}
      console.log('📊 [RAG] 解析后的items:', items)
      
      // 更新当前页的知识库列表
      knowledgeBases.value = items
      console.log('📊 [RAG] 更新后的knowledgeBases.value:', knowledgeBases.value)
      
      // 更新总数
      pagination.value.total = total
      console.log('📊 [RAG] 更新后的pagination:', pagination.value)
      
      // 更新全局知识库名称列表（去重）
      if (params.updateKbNames !== false) {
        const existingNames = new Set(kbNames.value)
        items.forEach(kb => {
          if (!existingNames.has(kb.name)) {
            kbNames.value.push(kb.name)
            existingNames.add(kb.name)
          }
        })
      }
      
      return knowledgeBases.value
    } catch (err) {
      console.error('Failed to fetch knowledge bases:', err)
      error.value = err.message || 'Failed to fetch knowledge bases'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 创建知识库
  async function createKnowledgeBase(data) {
    loading.value = true
    error.value = null

    try {
      const response = await ragApi.createKnowledgeBase(data)
      const newKb = response.data?.data

      if (newKb) {
        knowledgeBases.value.push(newKb)
      }

      return newKb
    } catch (err) {
      console.error('Failed to create knowledge base:', err)
      error.value = err.message || 'Failed to create knowledge base'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 更新知识库
  async function updateKnowledgeBase(data) {
    loading.value = true
    error.value = null

    try {
      const response = await ragApi.updateKnowledgeBase(data)
      const updatedKb = response.data?.data

      if (updatedKb) {
        const index = knowledgeBases.value.findIndex(kb => kb.id === updatedKb.id)
        if (index !== -1) {
          knowledgeBases.value[index] = updatedKb
        }
      }

      return updatedKb
    } catch (err) {
      console.error('Failed to update knowledge base:', err)
      error.value = err.message || 'Failed to update knowledge base'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 删除知识库
  async function deleteKnowledgeBase(id) {
    loading.value = true
    error.value = null

    try {
      await ragApi.deleteKnowledgeBase({ id })
      knowledgeBases.value = knowledgeBases.value.filter(kb => kb.id !== id)

      // 如果删除的是当前选中的知识库，清空选中状态
      if (currentKb.value?.id === id) {
        currentKb.value = null
      }
    } catch (err) {
      console.error('Failed to delete knowledge base:', err)
      error.value = err.message || 'Failed to delete knowledge base'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 导出知识库（返回后端导出的 JSON 数据）
  async function exportKnowledgeBase(id) {
    loading.value = true
    error.value = null

    try {
      const response = await ragApi.exportKnowledgeBase({ id })
      return response.data?.data
    } catch (err) {
      console.error('Failed to export knowledge base:', err)
      error.value = err.message || 'Failed to export knowledge base'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 获取知识库详情
  async function fetchKnowledgeBaseDetail(id) {
    loading.value = true
    error.value = null

    try {
      const response = await ragApi.getKnowledgeBaseDetail({ id })
      const kb = response.data?.data

      if (kb) {
        currentKb.value = kb
      }

      return kb
    } catch (err) {
      console.error('Failed to fetch knowledge base detail:', err)
      error.value = err.message || 'Failed to fetch knowledge base detail'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 更新知识库中文件的启用状态
  async function updateFileStatusInKb({ kbId, fileId, status }) {
    try {
      await ragApi.updateFileStatus({
        kb_id: kbId,
        file_id: fileId,
        status
      })
    } catch (err) {
      console.error('Failed to update file status:', err)
      throw err
    }
  }

  // 删除知识库中的单个文件
  async function deleteKbFile({ kbId, fileId }) {
    try {
      await ragApi.deleteFile({
        kb_id: kbId,
        file_id: fileId
      })
    } catch (err) {
      console.error('Failed to delete file:', err)
      throw err
    }
  }

  // 设置当前知识库
  function setCurrentKb(kb) {
    currentKb.value = kb
  }

  // 清除错误
  function clearError() {
    error.value = null
  }

  // 重置状态
  function reset() {
    knowledgeBases.value = []
    currentKb.value = null
    uploadingFiles.value = []
    uploadProgress.value = {}
    uploadQueue.value = []
    isUploading.value = false
    error.value = null
    loading.value = false
    pagination.value = {
      page: 1,
      pageSize: 10,
      total: 0
    }
    kbNames.value = []
  }

  // 分页相关方法
  function setPage(page) {
    pagination.value.page = page
  }

  function setPageSize(pageSize) {
    pagination.value.pageSize = pageSize
    pagination.value.page = 1 // 重置到第一页
  }

  // 获取知识库名称列表
  function getKbNames() {
    return kbNames.value
  }

  // 获取知识库名称列表（从服务器）
  async function fetchKnowledgeBaseNameList() {
    loading.value = true
    error.value = null

    try {
      const response = await ragApi.getKnowledgeBaseNameList()
      const items = response.data?.data?.items || []

      // 更新全局知识库名称列表
      // items 是对象数组，提取name字段
      kbNames.value = items.map(item => item.name)

      // 同时更新知识库列表（包含id和name）
      knowledgeBases.value = items.map(item => ({
        id: item.id,
        name: item.name
      }))

      return items
    } catch (err) {
      console.error('Failed to fetch knowledge base name list:', err)
      error.value = err.message || 'Failed to fetch knowledge base name list'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 上传单个文件并提交异步向量化任务（仅提交，不等待完成）
   * 流程：上传文件 -> 调用 process 启动后端异步任务 -> 返回 fileId/filename；
   * 实际处理状态请通过 pollFileStatus 轮询获取。
   * @param {File} file - 文件对象
   * @param {Object} options - 配置选项
   * @returns {Promise<Object>} - { fileId, filename, fileInfo, processResult }
   */
  async function uploadSingleFile(file, options = {}) {
    const { 
      maxSize = 1024 * 1024 * 1024, // 默认1GB
      onProgress = null,
      kbId = null,
      command = 'create',
      chunkStrategy = 'fixed',
      chunkParams = {}
    } = options

    try {
      // 限制单文件大小
      if (file.size > maxSize) {
        const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(1)
        throw new Error(`文件超过大小限制（最大 ${maxSizeMB}MB）`)
      }

      // 创建FormData
      const formData = new FormData()
      formData.append('file', file)
      if (kbId) {
        formData.append('kbId', String(kbId))
      }

      // 上传文件
      const uploadResponse = await ragApi.uploadFile(formData, (progress) => {
        if (onProgress) {
          onProgress(progress)
        }
      })

      let fileId = uploadResponse.data?.data?.file_id
      const filename = uploadResponse.data?.data?.filename

      if (!filename) {
        throw new Error('上传失败：未返回文件名')
      }

      // 获取文件信息
      const fileInfo = {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: new Date(file.lastModified).toISOString()
      }

      // 如果是文本文件，获取字符数
      if (file.type.startsWith('text/')) {
        const content = await file.text()
        fileInfo.charCount = content.length
      }

      // 提交处理（后端异步执行向量化，立即返回 file_id）
      // 若 process 长时间 pending（网关/后端阻塞），超时后改用「文件名 + 知识库」轮询，避免界面卡死
      const processTimeoutMs = 15000
      let processResponse = null
      try {
        processResponse = await Promise.race([
          ragApi.processFile({
            filename,
            fileInfo,
            command,
            kbId,
            chunkStrategy,
            chunkParams
          }),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('process_timeout')), processTimeoutMs)
          )
        ])
      } catch (e) {
        if (e?.message === 'process_timeout') {
          // 超时不抛错，返回无 fileId，由轮询用 file_name + kb_id 查状态
          return { fileId: null, filename, fileInfo, processResult: null }
        }
        throw e
      }

      if (!fileId && processResponse?.data?.data?.file_id != null) {
        fileId = processResponse.data.data.file_id
      }

      return {
        fileId,
        filename,
        fileInfo,
        processResult: processResponse?.data ?? null
      }
    } catch (err) {
      const msg = err.response?.data?.message || err.message
      const status = err.response?.status
      const detail = status ? `[${status}] ${msg}` : msg
      console.error('文件上传/处理失败:', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        errorMessage: detail,
        response: err.response
      })
      error.value = detail || '文件上传失败'
      throw new Error(detail || '文件上传失败')
    }
  }

  /** 每批最多上传文件数 */
  const UPLOAD_BATCH_SIZE = 5

  /**
   * 批量上传文件：按批循环，每个文件先上传再向量化（上传 → process），每批最多 5 个文件，且受单文件大小限制
   * @param {File[]} files - 文件数组
   * @param {Object} options - 配置选项
   * @returns {Promise<Object>} - 上传结果 { success: Array, failed: Array }
   */
  async function uploadMultipleFiles(files, options = {}) {
    isUploading.value = true
    error.value = null

    const { 
      maxSize = 1024 * 1024 * 1024, // 默认 1GB
      batchSize = UPLOAD_BATCH_SIZE,
      kbId = null,
      command = 'create',
      chunkStrategy = 'fixed',
      chunkParams = {},
      onProgress = null
    } = options

    const results = {
      success: [],
      failed: []
    }

    try {
      // 先过滤超限文件，直接计入失败
      const maxSizeMB = (maxSize / (1024 * 1024)).toFixed(1)
      const validFiles = []
      const queueItems = files.map((file, index) => {
        const overSize = file.size > maxSize
        const item = {
          file,
          status: overSize ? 'failed' : 'pending',
          progress: 0,
          error: overSize ? `超过大小限制（最大 ${maxSizeMB}MB）` : null
        }
        if (overSize) {
          results.failed.push({ file: file.name, error: item.error })
        } else {
          validFiles.push({ file, index })
        }
        return item
      })
      uploadQueue.value = queueItems

      let completedCount = 0
      const total = files.length

      // 按批循环上传，每批最多 batchSize 个
      for (let start = 0; start < validFiles.length; start += batchSize) {
        const batch = validFiles.slice(start, start + batchSize)
        for (const { file, index } of batch) {
          const queueItem = uploadQueue.value[index]
          try {
            queueItem.status = 'uploading'

            const result = await uploadSingleFile(file, {
              maxSize,
              kbId,
              command,
              chunkStrategy,
              chunkParams,
              onProgress: (progress) => {
                queueItem.progress = progress
                if (onProgress) {
                  const overall = total > 0 ? Math.round(((completedCount * 100 + progress) / total))
                    : 100
                  onProgress({
                    current: completedCount + 1,
                    total,
                    fileProgress: progress,
                    overallProgress: overall
                  })
                }
              }
            })

            queueItem.status = 'completed'
            results.success.push({
              ...result,
              originalFileName: file.name
            })
          } catch (err) {
            queueItem.status = 'failed'
            queueItem.error = err.message
            results.failed.push({
              file: file.name,
              error: err.message
            })
          }
          completedCount += 1
        }
      }

      return results
    } finally {
      isUploading.value = false
      uploadQueue.value = []
    }
  }

  /**
   * 取消文件上传
   */
  function cancelUpload() {
    // TODO: 实现取消上传的逻辑
    isUploading.value = false
    uploadQueue.value = []
  }

  /**
   * 通过轮询获取文件处理状态（上传并提交 process 后调用，不阻塞上传流程）
   * @param {Object} params - 轮询参数
   * @param {number} params.fileId - 文件ID
   * @param {number} params.kbId - 知识库ID
   * @param {Function} params.onProgress - 进度回调 { embeddingStatus, embeddingProgress, embeddingStatusText, ... }
   * @param {Function} params.onComplete - 完成回调
   * @param {Function} params.onError - 错误回调
   * @param {number} params.interval - 轮询间隔（毫秒），默认 5 秒
   * @param {number} params.maxAttempts - 最大轮询次数，默认 720（约 1 小时）
   * @returns {Promise<{ promise, stop }>} - promise 为轮询 Promise，stop 用于停止轮询
   */
  async function pollFileStatus(params) {
    const {
      fileId = null,
      filename = null,
      kbId,
      onProgress = null,
      onComplete = null,
      onError = null,
      interval = 5000,  // 5 秒轮询一次
      maxAttempts = 720, // 720 * 5s ≈ 1 小时
    } = params

    if (!fileId && !filename) {
      return { promise: Promise.reject(new Error('需要 fileId 或 filename')), stop: () => {} }
    }

    let attempts = 0
    let polling = true
    let resolvedFileId = fileId

    const stopPolling = () => {
      polling = false
    }

    const statusPayload = () => {
      const base = { kb_id: kbId }
      if (resolvedFileId != null) base.file_id = resolvedFileId
      else if (filename) base.file_name = filename
      return base
    }

    const poll = async () => {
      while (polling && attempts < maxAttempts) {
        try {
          const response = await ragApi.checkFileStatus(statusPayload())

          const statusData = response.data?.data
          if (!statusData) {
            throw new Error('Invalid status response')
          }
          if (resolvedFileId == null && statusData.file_id != null) {
            resolvedFileId = statusData.file_id
          }

          if (onProgress) {
            onProgress({
              fileId: resolvedFileId ?? fileId,
              kbId,
              processingStatus: statusData.processing_status,
              embeddingStatus: statusData.embedding_status,
              embeddingStatusText: statusData.embedding_status_text,
              embeddingProgress: statusData.embedding_progress ?? 0,
              errorMessage: statusData.error_message
            })
          }

          if (statusData.processing_status === 'completed' || statusData.embedding_status === 3) {
            if (onComplete) {
              onComplete(statusData)
            }
            return statusData
          }

          if (statusData.processing_status === 'failed' || statusData.error_message || statusData.embedding_status === 4) {
            const error = new Error(statusData.error_message || '文件处理失败')
            if (onError) {
              onError(error)
            }
            throw error
          }

          await new Promise(resolve => setTimeout(resolve, interval))
          attempts++
        } catch (err) {
          const response = err?.response
          const message = response?.data?.message || err.message || ''
          const codeFromData = response?.data?.code
          const errorCode = typeof err.code !== 'undefined' ? err.code : codeFromData

          const notFound =
            response?.status === 404 ||
            codeFromData === 'DATA_NOT_FOUND' ||
            (message && /未找到|不存在|请提供/.test(message))

          const isDbError =
            typeof errorCode === 'number' &&
            errorCode >= 1006 &&
            errorCode <= 1013

          if ((notFound || isDbError) && attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, interval))
            attempts++
            continue
          }

          if (onError) {
            onError(err)
          }
          throw err
        }
      }

      if (attempts >= maxAttempts && polling) {
        throw new Error('文件处理超时')
      }
    }

    // 开始轮询
    const pollPromise = poll()

    return {
      promise: pollPromise,
      stop: stopPolling
    }
  }

  // 获取指定文件的知识片段列表
  async function fetchKnowledgeSegments({ fileId, pageNo = 1, pageSize = 20, status = null, sortBy = 'updated_at', sortOrder = 'desc' }) {
    loading.value = true
    error.value = null
    try {
      const response = await ragApi.getKnowledgeSegments({
        file_id: fileId,
        page_no: pageNo,
        page_size: pageSize,
        status: status,
        sort_by: sortBy,
        sort_order: sortOrder
      })
      // response.data.data.items 已经是对象数组，不需要再转换
      return response.data?.data?.items || []
    } catch (err) {
      console.error('Failed to fetch knowledge segments:', err)
      error.value = err.message || 'Failed to fetch knowledge segments'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 创建知识片段
  async function createKnowledgeSegment(data) {
    loading.value = true
    error.value = null
    try {
      const response = await ragApi.createKnowledgeSegment(data)
      return response.data?.data
    } catch (err) {
      console.error('Failed to create knowledge segment:', err)
      error.value = err.message || 'Failed to create knowledge segment'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 更新知识片段
  async function updateKnowledgeSegment({ id, content, status, title }) {
    loading.value = true
    error.value = null
    try {
      await ragApi.updateKnowledgeSegment({
        id,
        content,
        status,
        title
      })
    } catch (err) {
      console.error('Failed to update knowledge segment:', err)
      error.value = err.message || 'Failed to update knowledge segment'
      throw err
    } finally {
      loading.value = false
    }
  }

  // 删除知识片段
  async function deleteKnowledgeSegment(id) {
    loading.value = true
    error.value = null
    try {
      await ragApi.deleteKnowledgeSegment({ id })
    } catch (err) {
      console.error('Failed to delete knowledge segment:', err)
      error.value = err.message || 'Failed to delete knowledge segment'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // 状态
    knowledgeBases,
    currentKb,
    loading,
    error,
    uploadingFiles,
    uploadProgress,
    uploadQueue,
    isUploading,
    pagination,
    kbNames,

    // 计算属性
    kbList,
    isLoading,
    hasError,
    errorMessage,

    // 方法
    fetchKnowledgeBases,
    fetchKnowledgeBaseNameList,
    createKnowledgeBase,
    updateKnowledgeBase,
    deleteKnowledgeBase,
    exportKnowledgeBase,
    fetchKnowledgeBaseDetail,
    setCurrentKb,
    clearError,
    reset,
    setPage,
    setPageSize,
    getKbNames,
    fetchKnowledgeSegments,
    createKnowledgeSegment,
    updateKnowledgeSegment,
    deleteKnowledgeSegment,
    uploadSingleFile,
    uploadMultipleFiles,
    cancelUpload,
    pollFileStatus,
    updateFileStatusInKb,
    deleteKbFile
  }
})
