<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useRagStore } from '@/store/rag'
import { validateFiles, getFileInfo, formatFileSize } from '@/utils/fileHelper'

const { t } = useI18n()
const emit = defineEmits(['backToManage'])
const ragStore = useRagStore()
const router = useRouter()

const currentStep = ref(1)

// 步骤一：数据源
const dataSourceType = ref('upload') // upload | text
const uploadedFiles = ref([]) // 多文件选择 & 拖拽
const isDragOver = ref(false)
const inputText = ref('')
const fileInputRef = ref(null)

// 步骤二：生成方式
const mode = ref('new') // new | append
const newKbName = ref('')
const newKbType = ref('document')
const existingKbId = ref('')
const existingKbs = computed(() => ragStore.knowledgeBases.map(kb => ({ id: kb.id, name: kb.name })))

// 文档切割策略
const chunkStrategy = ref('fixed') // fixed | recursive | sliding | semantic
const chunkLength = ref(500) // 固定长度切割的切割长度
const chunkOverlap = ref(50) // 滑动窗口的重叠长度
const semanticModel = ref('default') // 语义切割的模型

// 步骤三：生成过程
const logs = ref([])
const isGenerating = ref(false)
const isFinished = ref(false)
const uploadProgress = ref(0)
const overallProgress = ref(0)
const currentUploadFile = ref(null)
const uploadResults = ref({ success: [], failed: [] })
/** 上次写入日志的上传进度（整数 0–100），用于节流，避免重复刷同一行 */
const lastUploadLogPct = ref(-1)
let timer = null

// 加载知识库名称列表
async function loadKnowledgeBaseNames() {
  try {
    await ragStore.fetchKnowledgeBaseNameList()
  } catch (error) {
    console.error('加载知识库名称列表失败:', error)
  }
}

// 组件挂载时不加载知识库列表
// 在进入阶段二时才加载知识库名称列表

// 文件状态枚举
const FILE_STATUS = {
  PENDING: 'pending',      // 等待处理
  UPLOADING: 'uploading',    // 正在上传
  PARSING: 'parsing',       // 正在解析
  CHUNKING: 'chunking',     // 正在分段切分
  EMBEDDING: 'embedding',   // 正在向量化
  COMPLETED: 'completed',   // 已完成
  FAILED: 'failed',        // 失败
  PAUSED: 'paused'         // 已暂停
}

// 文件状态映射
const statusMap = {
  pending: '等待处理',
  uploading: '正在上传',
  parsing: '正在解析',
  chunking: '正在分段切分',
  embedding: '正在向量化',
  completed: '知识生成完成',
  failed: '处理失败',
  paused: '已暂停'
}

// 计算属性
const completedFilesCount = computed(() => {
  return uploadedFiles.value.filter(f => f.status === FILE_STATUS.COMPLETED).length
})

const failedFilesCount = computed(() => {
  return uploadedFiles.value.filter(f => f.status === FILE_STATUS.FAILED).length
})

function handleNext() {
  if (currentStep.value === 1 && !canNextStep1.value) return
  if (currentStep.value === 2 && !canNextStep2.value) return

  if (currentStep.value === 1) {
    // 进入阶段二时，如果选择了"追加到已有知识库"，则加载知识库名称列表
    if (mode.value === 'append') {
      loadKnowledgeBaseNames()
    }
  }

  if (currentStep.value === 2) {
    // 使用真实后端流程：先创建知识库（新建模式），再上传并处理文件
    startGenerate()
  }

  if (currentStep.value < 3) {
    currentStep.value += 1
  }
}

function handlePrev() {
  if (currentStep.value > 1) {
    currentStep.value -= 1
  }
}

function handleDone() {
  // 完成后返回知识库管理页面
  emit('backToManage')
}

const canNextStep1 = ref(false)
const canNextStep2 = ref(false)

function validateStep1() {
  if (dataSourceType.value === 'upload') {
    canNextStep1.value = uploadedFiles.value.length > 0
  } else {
    canNextStep1.value = !!inputText.value.trim()
  }
}

function validateStep2() {
  if (mode.value === 'new') {
    canNextStep2.value = !!newKbName.value.trim()
  } else {
    canNextStep2.value = !!existingKbId.value
  }
}

function handleModeChange() {
  validateStep2()
  // 如果选择了"追加到已有知识库"，则加载知识库名称列表
  if (mode.value === 'append') {
    loadKnowledgeBaseNames()
  }
}

function handleFileChange(e) {
  const files = Array.from(e.target.files || [])
  appendFiles(files)
  validateStep1()
}

function appendFiles(files) {
  const existing = uploadedFiles.value.slice()
  files.forEach((f) => {
    if (!existing.find((it) => it.name === f.name && it.size === f.size)) {
      existing.push({
        name: f.name,
        size: f.size,
        file: f, // 保存原始文件对象
        type: f.type,
        lastModified: f.lastModified,
        status: FILE_STATUS.PENDING,
        progress: 0
      })
    }
  })
  uploadedFiles.value = existing
}

async function walkEntry(entry, fileList) {
  if (entry.isFile) {
    await new Promise((resolve) => {
      entry.file((file) => {
        fileList.push(file)
        resolve()
      })
    })
  } else if (entry.isDirectory) {
    const reader = entry.createReader()
    await new Promise((resolve) => {
      const entries = []
      const readBatch = () => {
        reader.readEntries((batch) => {
          if (!batch.length) {
            Promise.all(entries.map((child) => walkEntry(child, fileList))).then(resolve)
          } else {
            entries.push(...batch)
            readBatch()
          }
        })
      }
      readBatch()
    })
  }
}

async function handleDrop(e) {
  e.preventDefault()
  isDragOver.value = false

  const dt = e.dataTransfer
  if (!dt) return

  const fileList = []

  if (dt.items && dt.items.length) {
    const entries = []
    for (let i = 0; i < dt.items.length; i += 1) {
      const item = dt.items[i]
      const entry = item.webkitGetAsEntry && item.webkitGetAsEntry()
      if (entry) entries.push(entry)
    }
    if (entries.length) {
      for (const entry of entries) {
        // eslint-disable-next-line no-await-in-loop
        await walkEntry(entry, fileList)
      }
    }
  }

  if (!fileList.length && dt.files && dt.files.length) {
    appendFiles(Array.from(dt.files))
  } else if (fileList.length) {
    // 处理文件夹中的文件，确保是File对象
    const fileObjects = fileList.map(f => {
      if (f instanceof File) return f
      // 如果不是File对象，创建新的File对象
      return new File([f], f.name, { type: f.type || 'application/octet-stream' })
    })
    appendFiles(fileObjects)
  }

  validateStep1()
}

function handleDragOver(e) {
  e.preventDefault()
  isDragOver.value = true
}

function handleDragLeave(e) {
  e.preventDefault()
  isDragOver.value = false
}

function handleDropZoneClick() {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

async function startGenerate() {
  if (isGenerating.value || isFinished.value) return
  isGenerating.value = true
  logs.value = []
  uploadResults.value = { success: [], failed: [] }
  lastUploadLogPct.value = -1

  const targetName =
    mode.value === 'new'
      ? newKbName.value.trim() || t('rag.defaultName', '新知识库')
      : existingKbs.value.find((k) => k.id === existingKbId.value)?.name || ''

  // 如果是文本输入，直接处理
  if (dataSourceType.value === 'text') {
    await processTextInput(targetName)
    return
  }

  // 如果是文件上传，处理文件上传
  if (dataSourceType.value === 'upload' && uploadedFiles.value.length > 0) {
    await processFileUpload(targetName)
  }
}

async function processTextInput(targetName) {
  addLog(t('rag.stepParseSource', '正在解析数据源…'), targetName)

  // 模拟处理文本
  await new Promise(resolve => setTimeout(resolve, 1000))

  addLog(t('rag.stepChunk', '正在分段切分文本…'), targetName)
  await new Promise(resolve => setTimeout(resolve, 1000))

  addLog(t('rag.stepEmbed', '正在向量化并写入知识库…'), targetName)
  await new Promise(resolve => setTimeout(resolve, 1000))

  addLog(t('rag.stepDone', '知识库生成完成。'), targetName)

  isGenerating.value = false
  isFinished.value = true
}

async function processFileUpload(targetName) {
  addLog(t('rag.stepParseSource', '正在解析数据源…'), targetName)

  // 使用保存的原始文件对象
  const filesToUpload = uploadedFiles.value.map(f => f.file)

  try {
    // 1. 准备目标知识库：新建模式先创建知识库，追加模式直接使用已选中的知识库
    let kbIdForUpload = null
    if (mode.value === 'append') {
      kbIdForUpload = existingKbId.value
    } else {
      const requestName =
        newKbName.value.trim() || t('rag.defaultName', '新知识库')

      const createReq = {
        name: requestName,
        kb_type: newKbType.value || 'document',
        description: '',
        chunk_strategy: chunkStrategy.value,
        chunk_params: {
          chunkLength: chunkLength.value,
          chunkOverlap: chunkOverlap.value,
          semanticModel: semanticModel.value
        }
      }

      try {
        const newKb = await ragStore.createKnowledgeBase(createReq)
        kbIdForUpload = newKb?.id
        if (!kbIdForUpload) {
          throw new Error('知识库创建失败，未返回ID')
        }
      } catch (e) {
        console.error('创建知识库失败:', e)
        addLog(
          t('rag.uploadError', '文件上传失败: {error}')
            .replace('{error}', e.message || '创建知识库失败'),
          requestName,
          true
        )
        isGenerating.value = false
        isFinished.value = true
        return
      }
    }

    // 2. 使用 store 的批量上传功能，将文件上传并关联到指定知识库
    // 使用 store 的批量上传功能
    const results = await ragStore.uploadMultipleFiles(filesToUpload, {
      maxSize: 1024 * 1024 * 1024,
      kbId: kbIdForUpload,
      command: mode.value === 'new' ? 'create' : 'append',
      chunkStrategy: chunkStrategy.value,
      chunkParams: {
        chunkLength: chunkLength.value,
        chunkOverlap: chunkOverlap.value,
        semanticModel: semanticModel.value
      },
      onProgress: (progress) => {
        const filePct = Number(progress.fileProgress)
        const overallPct = Number(progress.overallProgress)
        const pct = Math.min(100, Math.max(0, (Number.isFinite(filePct) ? filePct : (Number.isFinite(overallPct) ? overallPct : 0))))
        uploadProgress.value = Number.isFinite(overallPct) ? overallPct : pct
        const fileName = filesToUpload[progress.current - 1]?.name
        currentUploadFile.value = fileName
        const displayPct = Math.round(pct)
        // 仅当进度整数变化时更新日志；同一行更新数字，不逐行刷
        if (displayPct !== lastUploadLogPct.value) {
          lastUploadLogPct.value = displayPct
          const fileLabel = fileName || t('rag.unknownFile', '未知文件')
          const msg = `${t('rag.uploadingFileLabel', '正在上传文件')} ${fileLabel} (${displayPct}%)`
          setProgressLog(msg, targetName)
        }
      }
    })

    uploadResults.value = results

    // 记录上传结果（用模板字符串保证数量一定显示）
    if (results.success.length > 0) {
      const n = results.success.length
      addLog(`${t('rag.uploadSuccessLabel', '成功上传')} ${n} ${t('rag.uploadFilesUnit', '个文件')}`, targetName)
    }

    if (results.failed.length > 0) {
      console.error('上传失败的文件列表:', results.failed)
      const n = results.failed.length
      addLog(`${n} ${t('rag.uploadFailedSuffix', '个文件上传失败')}`,
        targetName
      )
      results.failed.forEach(failed => {
        console.error('文件上传失败详情:', {
          fileName: failed.file,
          error: failed.error
        })
        addLog(
          t('rag.fileUploadError', '文件 {file} 上传失败: {error}')
            .replace('{file}', failed.file || '未知文件')
            .replace('{error}', failed.error || '未知错误'),
          targetName,
          true // 标记为错误，显示红色
        )
      })
    }

    // 异步流程：上传已完成，仅通过轮询获取处理状态
    if (results.success.length > 0) {
      addLog(t('rag.stepChunk', '正在分段切分文本…'), targetName)
      addLog(t('rag.pollingStatus', '已提交向量化任务，通过轮询获取处理状态…'), targetName)

      const getDisplayName = (result) =>
        result.originalFileName || result.fileInfo?.name || result.filename

      // 立即将已提交的文件从「等待处理」改为「正在向量化 0%」，避免列表一直显示等待
      results.success.forEach((result) => {
        const displayName = getDisplayName(result)
        const fileItem = uploadedFiles.value.find(
          f =>
            f.name === displayName ||
            f.file?.name === displayName ||
            f.name === result.filename ||
            f.file?.name === result.filename
        )
        if (fileItem) updateFileStatus(fileItem, FILE_STATUS.EMBEDDING, 0)
      })

      const pollPromises = results.success.map(async (result) => {
        const { fileId, filename } = result
        const displayName = getDisplayName(result)
        const fileItem = uploadedFiles.value.find(
          f =>
            f.name === displayName ||
            f.file?.name === displayName ||
            f.name === filename ||
            f.file?.name === filename
        )
        try {
          const { promise: pollPromise } = await ragStore.pollFileStatus({
            fileId: fileId ?? undefined,
            filename: displayName || filename || undefined,
            kbId: kbIdForUpload,
            interval: 5000,
            maxAttempts: 720,
            onProgress: (status) => {
              console.log('轮询返回的status数据:', status)
              // 后端返回的embeddingProgress是0-1的小数，需要乘以100转换为百分比
              let progress = Math.round((status.embeddingProgress ?? 0) * 100)
              // 如果状态是完成，强制设为100%
              if (status.processingStatus === 'completed') {
                progress = 100
              }
              console.log('计算后的progress:', progress)
              if (fileItem) {
                console.log('更新文件状态:', fileItem.name, progress)
                updateFileStatus(fileItem, FILE_STATUS.EMBEDDING, progress)
              }
              const statusText = status.embeddingStatusText || ''
              console.log('statusText:', statusText)
              console.log('filename:', displayName || filename)
              console.log('progress:', progress)
              console.log('typeof progress:', typeof progress)
              // 直接使用字符串拼接，确保 progress 能正确显示
              const msg = statusText
                ? `${statusText} 进度: ${progress}%`
                : `向量化进度: ${progress}%`
              console.log('msg:', msg)
              setProgressLog(msg, targetName)
            },
            onComplete: (status) => {
              if (fileItem) {
                updateFileStatus(fileItem, FILE_STATUS.COMPLETED, 100)
              }
              addLog(
                t('rag.fileComplete', '文件 {file} 处理完成')
                  .replace('{file}', displayName || filename),
                targetName
              )
            },
            onError: (error) => {
              if (fileItem) {
                updateFileStatus(fileItem, FILE_STATUS.FAILED)
              }
              const errorMsg = error.message || error.toString() || '未知错误'
              addLog(
                t('rag.fileError', '文件 {file} 处理失败: {error}')
                  .replace('{file}', displayName || filename)
                  .replace('{error}', errorMsg),
                targetName,
                true
              )
            }
          })

          await pollPromise
        } catch (error) {
          console.error(`文件 ${displayName || filename} (fileId: ${fileId}) 轮询失败:`, error)
          const errorMsg = error.message || error.toString() || '未知错误'
          addLog(
            t('rag.fileError', '文件 {file} 处理失败: {error}')
              .replace('{file}', displayName || filename)
              .replace('{error}', errorMsg),
            targetName,
            true
          )
        }
      })

      // 等待所有文件处理完成
      await Promise.all(pollPromises)

      addLog(t('rag.stepEmbed', '正在向量化并写入知识库…'), targetName)
      addLog(t('rag.stepDone', '知识库生成完成。'), targetName)
    }
  } catch (error) {
    console.error('文件上传失败:', {
      errorMessage: error.message,
      errorStack: error.stack,
      response: error.response,
      request: error.request,
      config: error.config
    })
    addLog(
      t('rag.uploadError', '文件上传失败: {error}')
        .replace('{error}', error.message || '未知错误'),
      targetName,
      true // 标记为错误，显示红色
    )
  } finally {
    isGenerating.value = false
    isFinished.value = true
    currentUploadFile.value = null
  }
}

function addLog(message, targetName, isError = false) {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  logs.value.push({
    message: `[${time}] ${message.replace('{name}', targetName)}`,
    isError
  })
}

/** 进度日志：在同一行更新数字，不逐行刷。找到最后一条 isProgress 则更新，否则追加一条并标记 isProgress */
function setProgressLog(message, targetName) {
  const time = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  const full = `[${time}] ${message.replace('{name}', targetName)}`
  const lastIdx = logs.value.length - 1
  if (lastIdx >= 0 && logs.value[lastIdx].isProgress) {
    logs.value[lastIdx].message = full
    return
  }
  logs.value.push({ message: full, isError: false, isProgress: true })
}

function clearLogs() {
  logs.value = []
}

function getFileStatusText(status) {
  return statusMap[status] || status
}

function updateOverallProgress() {
  console.log('updateOverallProgress调用, uploadedFiles:', uploadedFiles.value.map(f => ({ name: f.name, status: f.status, progress: f.progress })))
  if (uploadedFiles.value.length === 0) {
    overallProgress.value = 0
    return
  }

  const totalProgress = uploadedFiles.value.reduce((sum, file) => {
    return sum + (file.progress || 0)
  }, 0)

  overallProgress.value = Math.round(totalProgress / uploadedFiles.value.length)
  console.log('计算后的overallProgress:', overallProgress.value)
}

function updateFileStatus(file, status, progress = null) {
  console.log('updateFileStatus调用:', file.name, status, progress)
  // 直接更新传入的file对象（响应式）
  file.status = status
  if (progress !== null) {
    file.progress = progress
  }
  updateOverallProgress()
}

async function startAllFiles() {
  if (isGenerating.value) return

  isGenerating.value = true
  isFinished.value = false

  // 重置所有文件状态
  uploadedFiles.value.forEach(file => {
    file.status = FILE_STATUS.PENDING
    file.progress = 0
  })
  // 更新总体进度
  updateOverallProgress()

  // 开始处理文件
  await processAllFiles()
}

async function processAllFiles() {
  const targetName =
    mode.value === 'new'
      ? newKbName.value.trim() || t('rag.defaultName', '新知识库')
      : existingKbs.value.find((k) => k.id === existingKbId.value)?.name || ''

  addLog(t('rag.stepParseSource', '开始处理文件…'), targetName)

  // 分批处理文件，每批最多5个，总大小不超过50MB
  const BATCH_SIZE = 5
  const MAX_BATCH_SIZE = 50 * 1024 * 1024 // 50MB

  const pendingFiles = uploadedFiles.value.filter(
    file => file.status !== FILE_STATUS.PAUSED && file.status !== FILE_STATUS.COMPLETED
  )

  for (let i = 0; i < pendingFiles.length; i += BATCH_SIZE) {
    // 获取当前批次的文件
    const batch = []
    let batchSize = 0

    for (let j = i; j < Math.min(i + BATCH_SIZE, pendingFiles.length); j++) {
      const file = pendingFiles[j]
      if (batchSize + file.size > MAX_BATCH_SIZE) {
        break
      }
      batch.push(file)
      batchSize += file.size
    }

    if (batch.length === 0) {
      // 单个文件就超过50MB，单独处理
      batch.push(pendingFiles[i])
    }

    addLog(
      t('rag.batchUpload', '正在处理第 {batch} 批，共 {count} 个文件，总大小 {size}')
        .replace('{batch}', Math.floor(i / BATCH_SIZE) + 1)
        .replace('{count}', batch.length)
        .replace('{size}', formatFileSize(batchSize)),
      targetName
    )

    // 并发处理当前批次
    await Promise.all(batch.map(file => processSingleFile(file)))

    // 检查是否还有文件需要处理
    if (i + BATCH_SIZE >= pendingFiles.length) {
      break
    }
  }

  isGenerating.value = false
  isFinished.value = true
  addLog(t('rag.allCompleted', '所有文件处理完成'), targetName)
}

async function simulateProgress(file, startProgress, endProgress, duration) {
  const steps = 10
  const stepDuration = duration / steps
  const progressIncrement = (endProgress - startProgress) / steps

  for (let i = 0; i < steps; i++) {
    if (file.status === FILE_STATUS.PAUSED) {
      throw new Error('文件处理已暂停')
    }

    await new Promise(resolve => setTimeout(resolve, stepDuration))
    updateFileStatus(file, file.status, startProgress + progressIncrement * (i + 1))
  }
}

function pauseFile(file) {
  updateFileStatus(file, FILE_STATUS.PAUSED, file.progress)
  addLog(
    t('rag.filePaused', '文件 {file} 已暂停')
      .replace('{file}', file.name),
    ''
  )
}

function resumeFile(file) {
  updateFileStatus(file, FILE_STATUS.UPLOADING, file.progress)
  addLog(
    t('rag.fileResumed', '文件 {file} 已恢复')
      .replace('{file}', file.name),
    ''
  )

  // 重新处理该文件
  processSingleFile(file)
}

async function processSingleFile(file) {
  const targetName =
    mode.value === 'new'
      ? newKbName.value.trim() || t('rag.defaultName', '新知识库')
      : existingKbs.value.find((k) => k.id === existingKbId.value)?.name || ''

  try {
    if (file.progress < 30) {
      updateFileStatus(file, FILE_STATUS.UPLOADING)
      await simulateProgress(file, file.progress, 30, 1000)
    }

    if (file.progress < 50) {
      updateFileStatus(file, FILE_STATUS.PARSING)
      await simulateProgress(file, file.progress, 50, 800)
    }

    if (file.progress < 70) {
      updateFileStatus(file, FILE_STATUS.CHUNKING)
      await simulateProgress(file, file.progress, 70, 1200)
    }

    if (file.progress < 100) {
      updateFileStatus(file, FILE_STATUS.EMBEDDING)
      await simulateProgress(file, file.progress, 100, 1500)
    }

    updateFileStatus(file, FILE_STATUS.COMPLETED, 100)
    addLog(
      t('rag.fileCompleted', '文件 {file} 处理完成')
        .replace('{file}', file.name),
      targetName
    )
  } catch (error) {
    updateFileStatus(file, FILE_STATUS.FAILED, file.progress)
    addLog(
      t('rag.fileError', '文件 {file} 处理失败: {error}')
        .replace('{file}', file.name)
        .replace('{error}', error.message),
      targetName,
      true
    )
  }
}

function retryFile(file) {
  updateFileStatus(file, FILE_STATUS.PENDING, 0)
  processSingleFile(file)
}

function deleteFile(file) {
  const index = uploadedFiles.value.findIndex(f => f.name === file.name)
  if (index !== -1) {
    uploadedFiles.value.splice(index, 1)
    updateOverallProgress()
    addLog(
      t('rag.fileDeleted', '文件 {file} 已删除')
        .replace('{file}', file.name),
      ''
    )
    // 如果所有文件都被删除了，立即设置isFinished为true
    if (uploadedFiles.value.length === 0) {
      isGenerating.value = false
      isFinished.value = true
    }
  }
}

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<template>
  <div class="rag-create">
    <!-- 步骤条 -->
    <div class="wizard-steps">
      <div
        class="wizard-step"
        :class="{ active: currentStep === 1, done: currentStep > 1 }"
      >
        <span class="index">1</span>
        <span class="label">{{ t('rag.step1', '选择数据源') }}</span>
      </div>
      <div class="wizard-line" />
      <div
        class="wizard-step"
        :class="{ active: currentStep === 2, done: currentStep > 2 }"
      >
        <span class="index">2</span>
        <span class="label">{{ t('rag.step2', '选择生成方式') }}</span>
      </div>
      <div class="wizard-line" />
      <div
        class="wizard-step"
        :class="{ active: currentStep === 3, done: isFinished }"
      >
        <span class="index">3</span>
        <span class="label">{{ t('rag.step3', '生成知识') }}</span>
      </div>
    </div>

    <!-- 步骤内容 -->
    <div class="wizard-body">
      <div class="wizard-toolbar">
        <button
          type="button"
          class="btn-secondary rag-back-btn"
          :aria-label="t('rag.backToKb', '返回知识库列表')"
          @click="emit('backToManage')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="9" />
            <polyline points="13.5 8 9.5 12 13.5 16" />
            <line x1="15" y1="12" x2="9.5" y2="12" />
          </svg>
        </button>
      </div>
      <!-- Step 1 -->
      <div v-if="currentStep === 1" class="step-card">
        <p class="step-desc">
          {{ t('rag.step1Desc', '支持 pdf、txt、office、html 文件导入，也可以直接粘贴文本。') }}
        </p>

        <div class="field-group">
          <label class="field-label">{{ t('rag.dataSourceType', '数据源类型') }}</label>
          <div class="radio-group">
            <label class="radio-item">
              <input
                v-model="dataSourceType"
                type="radio"
                value="upload"
                @change="validateStep1"
              />
              <span>{{ t('rag.dataSourceUpload', '上传文件') }}</span>
            </label>
            <label class="radio-item">
              <input
                v-model="dataSourceType"
                type="radio"
                value="text"
                @change="validateStep1"
              />
              <span>{{ t('rag.dataSourceText', '粘贴文本') }}</span>
            </label>
          </div>
        </div>

        <div v-if="dataSourceType === 'upload'" class="field-group">
          <label class="field-label">{{ t('rag.uploadFile', '上传文件') }}</label>
          <input ref="fileInputRef" type="file" class="file-input" multiple @change="handleFileChange" />
          <div
            class="drop-zone"
            :class="{ 'is-drag-over': isDragOver }"
            @dragover="handleDragOver"
            @dragleave="handleDragLeave"
            @drop="handleDrop"
            @click="handleDropZoneClick"
          >
            <div class="drop-zone-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M7 18a5 5 0 1 1 .9-9.9A7 7 0 1 1 19 17h-2" />
                <path d="M12 12v6" />
                <path d="M9 15l3-3 3 3" />
              </svg>
            </div>
            <div class="drop-zone-main">{{ t('rag.uploadHintMain', '拖拽文件至此或点击上传') }}</div>
            <div class="drop-zone-sub">.txt / .markdown / .pdf，单个文件≤20M</div>
          </div>
          <div v-if="uploadedFiles.length" class="selected-file-list">
            <div class="selected-file-item" v-for="file in uploadedFiles" :key="file.name">
              <span class="file-dot" />
              <span class="file-name">{{ file.name }}</span>
            </div>
          </div>
        </div>

        <div v-else class="field-group">
          <label class="field-label">{{ t('rag.textContent', '文本内容') }}</label>
          <textarea
            v-model="inputText"
            class="text-area"
            rows="6"
            :placeholder="t('rag.textPlaceholder', '在此粘贴或输入需要生成知识的文本…')"
            @input="validateStep1"
          />
        </div>
      </div>

      <!-- Step 2 -->
      <div v-else-if="currentStep === 2" class="step-card">
        <p class="step-desc">
          {{ t('rag.step2Desc', '可以创建全新的知识库，或将数据追加到已有知识库中。') }}
        </p>

        <div class="field-group">
          <label class="field-label">{{ t('rag.genMode', '生成方式') }}</label>
          <div class="radio-group">
            <label class="radio-item">
              <input
                v-model="mode"
                type="radio"
                value="new"
                @change="handleModeChange"
              />
              <span>{{ t('rag.modeNew', '创建新知识库') }}</span>
            </label>
            <label class="radio-item">
              <input
                v-model="mode"
                type="radio"
                value="append"
                @change="handleModeChange"
              />
              <span>{{ t('rag.modeAppend', '追加到已有知识库') }}</span>
            </label>
          </div>
        </div>

        <div v-if="mode === 'new'" class="field-group">
          <label class="field-label">{{ t('rag.columns.name') }}</label>
          <input
            v-model="newKbName"
            type="text"
            class="text-input"
            :placeholder="t('rag.namePlaceholder')"
            @input="validateStep2"
          />

          <label class="field-label">{{ t('rag.columns.type') }}</label>
          <select v-model="newKbType" class="select-input">
            <option value="document">{{ t('rag.types.document') }}</option>
            <option value="vector">{{ t('rag.types.vector') }}</option>
          </select>
        </div>

        <div v-else class="field-group">
          <label class="field-label">{{ t('rag.appendTarget', '选择目标知识库') }}</label>
          <select v-model="existingKbId" class="select-input" @change="validateStep2">
            <option value="" disabled>{{ t('rag.appendPlaceholder', '请选择知识库') }}</option>
            <option v-for="kb in existingKbs" :key="kb.id" :value="kb.id">
              {{ kb.name }}
            </option>
          </select>
        </div>

        <!-- 文档切割策略 -->
        <div class="field-group chunk-strategy-section">
          <label class="field-label">{{ t('rag.chunkStrategy', '文档切割策略') }}</label>

          <div class="strategy-selector">
            <label class="strategy-option">
              <input type="radio" v-model="chunkStrategy" value="fixed" @change="validateStep2" />
              <div class="strategy-content">
                <span class="strategy-name">{{ t('rag.strategyFixed', '固定长度切割') }}</span>
                <span class="strategy-desc">{{ t('rag.strategyFixedDesc', '适合通用场景，文本结构不明确，可能切断语义') }}</span>
              </div>
            </label>
            <label class="strategy-option">
              <input type="radio" v-model="chunkStrategy" value="recursive" @change="validateStep2" />
              <div class="strategy-content">
                <span class="strategy-name">{{ t('rag.strategyRecursive', '递归式切割') }}</span>
                <span class="strategy-desc">{{ t('rag.strategyRecursiveDesc', '按层级递归切割，适合长文档、结构化文档') }}</span>
              </div>
            </label>
            <label class="strategy-option">
              <input type="radio" v-model="chunkStrategy" value="sliding" @change="validateStep2" />
              <div class="strategy-content">
                <span class="strategy-name">{{ t('rag.strategySliding', '滑动窗口') }}</span>
                <span class="strategy-desc">{{ t('rag.strategySlidingDesc', '对上下文连续性要求极高的场景，存储和计算成本高，检索结果冗余') }}</span>
              </div>
            </label>
            <label class="strategy-option">
              <input type="radio" v-model="chunkStrategy" value="semantic" @change="validateStep2" />
              <div class="strategy-content">
                <span class="strategy-name">{{ t('rag.strategySemantic', '语义切割') }}</span>
                <span class="strategy-desc">{{ t('rag.strategySemanticDesc', '利用模型识别语义边界进行切割，切割最精准，语义最完整，计算成本最高') }}</span>
              </div>
            </label>
          </div>

          <!-- 固定长度切割参数 -->
          <div v-if="chunkStrategy === 'fixed'" class="strategy-params">
            <div class="field-group">
              <label class="field-label">{{ t('rag.chunkLength', '切割长度') }}</label>
              <input 
                v-model.number="chunkLength" 
                type="number" 
                class="text-input"
                :min="100"
                :max="2000"
                :step="50"
                @input="validateStep2"
              />
              <span class="param-hint">{{ t('rag.chunkLengthHint', '建议范围：100-2000字符') }}</span>
            </div>
          </div>

          <!-- 滑动窗口参数 -->
          <div v-if="chunkStrategy === 'sliding'" class="strategy-params">
            <div class="field-group">
              <label class="field-label">{{ t('rag.chunkLength', '切割长度') }}</label>
              <input 
                v-model.number="chunkLength" 
                type="number" 
                class="text-input"
                :min="100"
                :max="2000"
                :step="50"
                @input="validateStep2"
              />
            </div>
            <div class="field-group">
              <label class="field-label">{{ t('rag.chunkOverlap', '重叠长度') }}</label>
              <input 
                v-model.number="chunkOverlap" 
                type="number" 
                class="text-input"
                :min="0"
                :max="500"
                :step="10"
                @input="validateStep2"
              />
              <span class="param-hint">{{ t('rag.chunkOverlapHint', '建议范围：0-500字符，通常为切割长度的10-20%') }}</span>
            </div>
          </div>

          <!-- 语义切割参数 -->
          <div v-if="chunkStrategy === 'semantic'" class="strategy-params">
            <div class="field-group">
              <label class="field-label">{{ t('rag.semanticModel', '语义模型') }}</label>
              <select v-model="semanticModel" class="select-input" @change="validateStep2">
                <option value="default">{{ t('rag.modelDefault', '默认模型') }}</option>
                <option value="advanced">{{ t('rag.modelAdvanced', '高级模型') }}</option>
                <option value="custom">{{ t('rag.modelCustom', '自定义模型') }}</option>
              </select>
              <span class="param-hint">{{ t('rag.semanticModelHint', '不同模型对语义边界的识别精度和计算成本不同') }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3 -->
      <div v-else class="step-card">
        <p class="step-desc">
          {{ t('rag.step3Desc', '系统正在根据数据源生成向量知识，请不要关闭页面。') }}
        </p>

        <!-- 总体进度条 -->
        <div v-if="isGenerating || isFinished" class="overall-progress-section">
          <div class="progress-info">
            <span class="progress-label">{{ t('rag.overallProgress', '总体进度') }}</span>
            <span class="progress-value">{{ overallProgress }}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: overallProgress + '%' }"></div>
          </div>
          <div class="progress-stats">
            <span>{{ t('rag.completedFiles', '已完成') }}: {{ completedFilesCount }}/{{ uploadedFiles.length }}</span>
            <span>{{ t('rag.failedFiles', '失败') }}: {{ failedFilesCount }}</span>
          </div>
        </div>

        <!-- 文件列表 -->
        <div class="file-list-section">
          <div class="file-list-header">
            <span class="file-list-title">{{ t('rag.fileList', '文件列表') }}</span>
            <button v-if="!isGenerating && !isFinished" @click="startAllFiles" class="btn-primary btn-sm">
              {{ t('rag.startAll', '全部开始') }}
            </button>
          </div>

          <div class="file-list">
            <div 
              v-for="(file, index) in uploadedFiles" 
              :key="file.name"
              class="file-item"
              :class="{ 
                'processing': file.status === FILE_STATUS.EMBEDDING || file.status === FILE_STATUS.UPLOADING || file.status === FILE_STATUS.PARSING || file.status === FILE_STATUS.CHUNKING,
                'completed': file.status === FILE_STATUS.COMPLETED,
                'failed': file.status === FILE_STATUS.FAILED,
                'paused': file.status === FILE_STATUS.PAUSED
              }"
            >
              <!-- 文件信息 -->
              <div class="file-info">
                <div class="file-name">{{ file.name }}</div>
                <div class="file-meta">
                  <span class="file-size">{{ formatFileSize(file.size) }}</span>
                  <span class="file-status" :class="{ [`status-${file.status}`]: true }">
                    {{ getFileStatusText(file.status) }}
                  </span>
                  <button
                    @click="deleteFile(file)"
                    class="btn-icon btn-danger btn-sm"
                    :title="t('rag.delete', '删除')"
                  >
                    🗑
                  </button>
                </div>
              </div>

              <!-- 文件进度条（上传/向量化时显示） -->
              <div v-if="file.status === FILE_STATUS.EMBEDDING || file.status === FILE_STATUS.UPLOADING || file.status === FILE_STATUS.PARSING || file.status === FILE_STATUS.CHUNKING" class="file-progress">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: (file.progress ?? 0) + '%' }"></div>
                </div>
                <span class="progress-value">{{ file.progress ?? 0 }}%</span>
              </div>

              <!-- 操作按钮 -->
              <div class="file-actions">
                <button 
                  v-if="file.status === FILE_STATUS.EMBEDDING || file.status === FILE_STATUS.UPLOADING || file.status === FILE_STATUS.PARSING || file.status === FILE_STATUS.CHUNKING" 
                  @click="pauseFile(file)"
                  class="btn-icon"
                  :title="t('rag.pause', '暂停')"
                >
                  ⏸
                </button>
                <button 
                  v-if="file.status === FILE_STATUS.PAUSED" 
                  @click="resumeFile(file)"
                  class="btn-icon"
                  :title="t('rag.resume', '继续')"
                >
                  ▶
                </button>
                <button 
                  v-if="file.status === FILE_STATUS.FAILED" 
                  @click="retryFile(file)"
                  class="btn-icon"
                  :title="t('rag.retry', '重试')"
                >🔄
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 日志面板 -->
        <div class="log-panel">
          <div class="log-header">
            <span class="log-title">{{ t('rag.logs', '日志') }}</span>
            <button @click="clearLogs" class="btn-text btn-sm">{{ t('rag.clearLogs', '清空日志') }}</button>
          </div>
          <div v-if="logs.length === 0" class="log-empty">
            {{ t('rag.logEmpty', '准备开始生成知识…') }}
          </div>
          <div v-else class="log-lines">
            <div 
              v-for="(line, idx) in logs" 
              :key="idx" 
              class="log-line"
              :class="{ 'error': line.isError }"
            >
              {{ line.message }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部操作区 -->
    <div class="wizard-actions">
      <button
        type="button"
        class="btn-secondary"
        :disabled="currentStep === 1"
        @click="handlePrev"
      >
        {{ t('common.prev', '上一步') }}
      </button>
      <button
        v-if="currentStep < 3"
        type="button"
        class="btn-primary"
        :disabled="(currentStep === 1 && !canNextStep1) || (currentStep === 2 && !canNextStep2)"
        @click="handleNext"
      >
        {{ t('common.next', '下一步') }}
      </button>
      <button
        v-else
        type="button"
        class="btn-primary"
        :disabled="!isFinished"
        @click="handleDone"
      >
        {{ isFinished ? t('common.done', '完成') : t('rag.generating', '生成中…') }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.rag-create {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wizard-steps {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wizard-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.wizard-step .index {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
}

.wizard-step.active .index {
  background: var(--accent-gradient);
  border-color: transparent;
  color: var(--button-text);
}

.wizard-step.done .index {
  background: rgba(22, 163, 74, 0.2);
  border-color: rgba(22, 163, 74, 0.6);
  color: #22c55e;
}

.wizard-step .label {
  white-space: nowrap;
}

.wizard-step.active .label {
  color: var(--text-primary);
  font-weight: 600;
}

.wizard-line {
  flex: 1;
  height: 1px;
  background: var(--border-primary);
  opacity: 0.6;
}

.wizard-body {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  padding: 12px 18px 18px;
  min-height: 260px;
}

.wizard-toolbar {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 8px;
}

.step-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.file-input {
  display: none;
}

.drop-zone {
  margin-top: 14px;
  padding: 40px 12px 52px;
  border-radius: 8px;
  border: 1px dashed rgba(148, 163, 184, 0.6);
  background: rgba(10, 23, 42, 0.8);
  color: var(--text-secondary);
  text-align: center;
  transition: all 0.2s ease;
  cursor: pointer;
}

.drop-zone.is-drag-over {
  border-color: var(--accent-primary);
  background: rgba(34, 197, 94, 0.08);
  color: var(--accent-primary);
}

.drop-zone-icon {
  width: 44px;
  height: 44px;
  margin: 0 auto 10px;
  color: var(--text-secondary);
}

.drop-zone-icon svg {
  width: 44px;
  height: 44px;
}

.drop-zone-main {
  font-size: 1.05rem;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.drop-zone-sub {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.selected-file-list {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.9);
}

.selected-file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.selected-file-item + .selected-file-item {
  margin-top: 4px;
}

.file-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
}

.file-name {
  word-break: break-all;
}

.text-area {
  resize: vertical;
  min-height: 120px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-family: var(--font-mono, monospace);
  font-size: 0.85rem;
}

.text-input,
.select-input {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.log-panel {
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: #020617;
  padding: 10px 12px;
  max-height: 220px;
  overflow: auto;
  font-family: var(--font-mono, monospace);
  font-size: 0.8rem;
}

.log-empty {
  color: var(--text-secondary);
}

.log-lines {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.log-line {
  color: var(--text-primary);

  &.error {
    color: #ef4444;
    font-weight: 500;
  }
}

.upload-progress-section {
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid var(--border-primary);
}

.overall-progress-section {
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid var(--border-primary);

  .progress-stats {
    display: flex;
    gap: 20px;
    margin-top: 8px;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }
}

.file-list-section {
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-primary);
}

.file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.file-list-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  border-radius: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  transition: all 0.2s ease;

  &.processing {
    border-color: var(--accent-primary);
    background: rgba(34, 197, 94, 0.05);
  }

  &.completed {
    border-color: #22c55e;
    background: rgba(34, 197, 94, 0.08);
  }

  &.failed {
    border-color: #ef4444;
    background: rgba(239, 68, 68, 0.05);
  }

  &.paused {
    border-color: #f59e0b;
    background: rgba(245, 158, 11, 0.05);
  }
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  justify-content: space-between;
}

.file-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-all;
  flex: 1;
  min-width: 0;
  line-height: 1.2;
}

.file-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 0.75rem;
  color: var(--text-secondary);
  flex-shrink: 0;
  line-height: 1.2;
}

.file-size {
  color: var(--text-muted);
}

.file-status {
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 500;

  &.status-pending {
    color: #94a3b8;
    background: rgba(148, 163, 184, 0.1);
  }

  &.status-uploading {
    color: var(--accent-primary);
    background: rgba(34, 197, 94, 0.1);
  }

  &.status-parsing {
    color: #3b82f6;
    background: rgba(59, 130, 246, 0.1);
  }

  &.status-chunking {
    color: #8b5cf6;
    background: rgba(139, 92, 246, 0.1);
  }

  &.status-embedding {
    color: #ec4899;
    background: rgba(236, 72, 153, 0.1);
  }

  &.status-completed {
    color: #22c55e;
    background: rgba(34, 197, 94, 0.1);
  }

  &.status-failed {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
  }

  &.status-paused {
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.1);
  }
}

.file-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.file-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  margin-top: 2px;
}

.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: rgba(148, 163, 184, 0.1);
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(148, 163, 184, 0.2);
    color: var(--text-primary);
  }

  &.btn-danger:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }

  &.btn-sm {
    width: 24px;
    height: 24px;
    font-size: 1rem;
  }
}

.btn-primary {
  padding: 6px 16px;
  border: none;
  border-radius: 6px;
  background: var(--accent-primary);
  color: white;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    opacity: 0.9;
  }

  &.btn-sm {
    padding: 4px 12px;
    font-size: 0.8rem;
  }
}

.btn-text {
  padding: 4px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(148, 163, 184, 0.1);
    color: var(--text-primary);
  }

  &.btn-sm {
    padding: 2px 8px;
    font-size: 0.75rem;
  }
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.log-title {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.progress-value {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--accent-primary);
}

.progress-bar {
  height: 8px;
  background: rgba(148, 163, 184, 0.2);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: var(--accent-gradient);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.current-file {
  font-size: 0.85rem;
  color: var(--text-secondary);
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(34, 197, 94, 0.08);
}

.chunk-strategy-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-primary);
}

.strategy-selector {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.strategy-option {
  position: relative;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  cursor: pointer;
  transition: all 0.2s ease;

  input[type="radio"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
  }

  &:hover {
    border-color: var(--accent-primary);
    background: rgba(34, 197, 94, 0.05);
  }

  input:checked + .strategy-content {
    .strategy-name {
      color: var(--accent-primary);
      font-weight: 600;
    }
  }

  input:checked ~ .strategy-content::before {
    content: '';
    position: absolute;
    top: 8px;
    right: 8px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid var(--accent-primary);
    background: var(--accent-primary);
    box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
  }
}

.strategy-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.strategy-name {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
  transition: all 0.2s ease;
}

.strategy-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}

.strategy-params {
  margin-top: 16px;
  padding: 16px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-primary);
}

.param-hint {
  display: block;
  margin-top: 6px;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.4;
}

.wizard-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.rag-back-btn {
  padding: 4px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;

  svg {
    width: 22px;
    height: 22px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
    border-color: var(--accent-primary);
  }
}

.btn-primary,
.btn-secondary {
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 0.85rem;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-primary {
  background: var(--accent-gradient);
  color: var(--button-text);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

.btn-secondary {
  background: transparent;
  border-color: var(--border-primary);
  color: var(--text-secondary);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
