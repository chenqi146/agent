<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRagStore } from '@/store/rag'
import { ragApi } from '@/api/rag'
import { KB_TYPES } from '@/store/rag'

const { t } = useI18n()
const ragStore = useRagStore()

const loading = computed(() => ragStore.isLoading)
const list = computed(() => {
  const result = ragStore.knowledgeBases
  console.log('📊 [MngView] list计算属性被调用, ragStore.knowledgeBases:', ragStore.knowledgeBases)
  console.log('📊 [MngView] list计算属性返回值:', result)
  return result
})
const pagination = computed(() => ragStore.pagination)

// 加载知识库列表
async function loadList() {
  try {
    await ragStore.fetchKnowledgeBases()
  } catch (error) {
    console.error('Failed to load KB list:', error)
  }
}

// 分页处理
function handlePageChange(page) {
  ragStore.setPage(page)
  loadList()
}

onMounted(loadList)

const isFileView = ref(false)
const currentKb = ref(null)
const fileList = ref([])
const knowledgeList = ref([])
const activeDetailTab = ref('file')
const knowledgeTimeFilter = ref('all')
const knowledgeRecallFilter = ref('all')
const knowledgeSort = ref('recall_desc')

// --- 本体交互逻辑 (Frontend Mock) ---
const schemaLabels = ref([])
const ontologyOptions = computed(() => [
  { label: `${t('rag.ontology.allKbs')} (${t('rag.ontology.kb')})`, value: 'all' },
  ...schemaLabels.value.map(l => ({ label: `${l} (${t('rag.ontology.ontologyItem')})`, value: l }))
])
const selectedOntology = ref('all')
const ontologySearchQuery = ref('')
const ontologyStats = ref({
  total_nodes: 0,
  total_relations: 0,
  labels: {},
  total_recall_count: 0
})
const ontologyNodes = ref([])
const ontologyPagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})
const isOntologyLoading = ref(false)

// 加载本体统计信息
async function loadOntologyStats() {
  try {
    const res = await ragApi.getOntologyStatistics()
    if (res?.data?.data) {
      ontologyStats.value = res.data.data
    }
  } catch (error) {
    console.error('Failed to load ontology stats:', error)
  }
}

// 加载本体Schema（用于筛选选项）
async function loadOntologySchema() {
  try {
    const res = await ragApi.getOntologySchema()
    const data = res?.data?.data || {}
    const labels = data.labels || []
    schemaLabels.value = labels
  } catch (error) {
    console.error('Failed to load ontology schema:', error)
  }
}

// 加载本体节点数据
async function loadOntologyNodes() {
  if (selectedOntology.value === 'all') return
  
  isOntologyLoading.value = true
  try {
    const res = await ragApi.getOntologyNodes({
      label: selectedOntology.value,
      page: ontologyPagination.value.page,
      page_size: ontologyPagination.value.pageSize,
      keyword: ontologySearchQuery.value
    })
    const data = res?.data?.data || {}
    ontologyNodes.value = data.items || []
    ontologyPagination.value.total = data.total || 0
  } catch (error) {
    console.error('Failed to load ontology nodes:', error)
    ontologyNodes.value = []
  } finally {
    isOntologyLoading.value = false
  }
}

// 监听筛选变化
watch([selectedOntology, ontologySearchQuery], () => {
  ontologyPagination.value.page = 1
  if (selectedOntology.value !== 'all') {
    loadOntologyNodes()
  }
})

// 监听分页变化 (需要添加到模板中)
function handleOntologyPageChange(page) {
  ontologyPagination.value.page = page
  loadOntologyNodes()
}

// 初始化
onMounted(() => {
  loadList()
  loadOntologyStats()
  loadOntologySchema()
})

// 列表显示逻辑：如果是 'all' 显示知识库，否则显示本体节点
const isOntologyViewMode = computed(() => selectedOntology.value !== 'all')

const filteredList = computed(() => {
  if (isOntologyViewMode.value) {
    return ontologyNodes.value
  }
  
  // 知识库列表过滤
  if (!list.value || !Array.isArray(list.value)) {
    return []
  }
  let result = list.value
  
  if (ontologySearchQuery.value) {
    const q = ontologySearchQuery.value.toLowerCase()
    result = result.filter(item => 
      item.name.toLowerCase().includes(q)
    )
  }
  
  return result
})

// --- Ontology Edit Logic ---
const showOntologyEdit = ref(false)
const isOntologySaving = ref(false)
const ontologyForm = ref({
  id: null, // internal_id if editing
  name: '',
  label: '',
  properties: '{}'
})

function handleAddOntology() {
  ontologyForm.value = {
    id: null,
    name: '',
    label: selectedOntology.value !== 'all' ? selectedOntology.value : '',
    properties: '{}'
  }
  showOntologyEdit.value = true
}

function handleEditOntology(node) {
  // 过滤掉系统属性
  const props = { ...node.properties }
  delete props.id
  delete props.name
  delete props.created_at
  delete props.updated_at

  ontologyForm.value = {
    id: node.internal_id,
    name: node.name,
    label: node.labels[0] || '',
    properties: JSON.stringify(props, null, 2)
  }
  showOntologyEdit.value = true
}

async function handleDeleteOntology(node) {
  if (!confirm(t('rag.ontology.edit.deleteConfirm', { name: node.name }))) return
  
  try {
    await ragApi.deleteOntologyNode({
      id: node.internal_id
    })
    // Refresh list
    loadOntologyNodes()
    loadOntologyStats()
  } catch (error) {
    console.error('Failed to delete node:', error)
    alert(`${t('common.delete')} ${t('common.error')}: ${error.message || 'Unknown error'}`)
  }
}

function cancelOntologyEdit() {
  showOntologyEdit.value = false
  ontologyForm.value = { id: null, name: '', label: '', properties: '' }
}

async function saveOntologyNode() {
  if (!ontologyForm.value.name || !ontologyForm.value.label) {
    alert(t('rag.ontology.edit.nameLabelRequired'))
    return
  }
  
  let props = {}
  try {
    props = JSON.parse(ontologyForm.value.properties || '{}')
  } catch (e) {
    alert(t('rag.ontology.edit.invalidJson'))
    return
  }

  isOntologySaving.value = true
  try {
    if (ontologyForm.value.id) {
      // Update
      await ragApi.updateOntologyNode({
        id: ontologyForm.value.id,
        properties: {
          ...props,
          name: ontologyForm.value.name
        }
      })
    } else {
      // Create
      await ragApi.createOntologyNode({
        name: ontologyForm.value.name,
        label: ontologyForm.value.label,
        properties: props
      })
    }
    
    showOntologyEdit.value = false
    loadOntologyNodes()
    loadOntologyStats()
    loadOntologySchema() // In case new label was added
  } catch (error) {
    console.error('Failed to save node:', error)
    alert(`${t('rag.ontology.edit.save')} ${t('common.error')}: ${error.message || 'Unknown error'}`)
  } finally {
    isOntologySaving.value = false
  }
}

function handleBatchTag() {
  alert(t('rag.ontology.edit.batchTagFeature'))
}

async function loadKnowledgeList() {
  if (!currentKb.value) return
  knowledgeList.value = []
  const payload = {
    kb_id: currentKb.value.id
  }
  if (knowledgeTimeFilter.value !== 'all') {
    const map = {
      last7d: 7,
      last30d: 30,
      last90d: 90
    }
    const days = map[knowledgeTimeFilter.value]
    if (days) {
      payload.recent_days = days
    }
  }
  if (knowledgeRecallFilter.value === 'never') {
    payload.max_recall_count = 0
  } else if (knowledgeRecallFilter.value === 'has') {
    payload.min_recall_count = 1
  }
  if (knowledgeSort.value === 'recall_desc') {
    payload.sort_by = 'recall_count'
    payload.sort_order = 'desc'
  } else if (knowledgeSort.value === 'recall_asc') {
    payload.sort_by = 'recall_count'
    payload.sort_order = 'asc'
  } else if (knowledgeSort.value === 'time_desc') {
    payload.sort_by = 'upload_time'
    payload.sort_order = 'desc'
  } else if (knowledgeSort.value === 'time_asc') {
    payload.sort_by = 'upload_time'
    payload.sort_order = 'asc'
  }
  try {
    const resp = await ragApi.getKnowledgeList(payload)
    const data = resp?.data?.data || {}
    const items = data.items || []
    knowledgeList.value = items.map((it) => ({
      id: it.id,
      fileName: it.file_name,
      recallCount: it.recall_count,
      lastAccessTime: it.last_access_time || '-',
      avgScore: it.avg_score ?? '-',
      instructionScore: it.instruction_score ?? '-',
      relevanceScore: it.relevance_score ?? '-',
      isNoise: !!it.is_noise,
      isRedundant: !!it.is_redundant,
      createdAt: it.created_at || '-',
      updatedAt: it.updated_at || '-'
    }))
  } catch (error) {
    console.error('Failed to load knowledge info list:', error)
  }
}

async function viewKnowledge(item) {
  currentKb.value = item
  isFileView.value = true
  activeDetailTab.value = 'knowledge'
  knowledgeTimeFilter.value = 'all'
  knowledgeRecallFilter.value = 'all'
  knowledgeSort.value = 'recall_desc'
  await loadKnowledgeList()
}

async function openFileView(item) {
  currentKb.value = item
  isFileView.value = true
  activeDetailTab.value = 'file'
  fileList.value = []
  try {
    const data = await ragStore.exportKnowledgeBase(item.id)
    const files = data?.files || []
    fileList.value = files.map((f) => ({
      id: f.id,
      name: f.file_name,
      status: f.status === 1 ? 'available' : 'disabled',
      uploadTime: f.upload_time ? formatTime(f.upload_time) : '-',
      segmentModel: f.segmentation_type || '-',
      recallCount: f.recall_count ?? 0,
      charCount: f.file_char_count ?? 0,
      progress: f.status === 1 ? 100 : 0
    }))
  } catch (error) {
    console.error(t('rag.loadKbFilesFailed', { error: error.message }), error)
    alert(t('rag.loadKbFilesFailed', { error: error.message || t('common.unknown') }))
    isFileView.value = false
    currentKb.value = null
  }
}

function backToKbList() {
  isFileView.value = false
  currentKb.value = null
  fileList.value = []
  knowledgeList.value = []
  activeDetailTab.value = 'file'
}

async function onKnowledgeFilterChange() {
  if (activeDetailTab.value !== 'knowledge' || !isFileView.value) return
  await loadKnowledgeList()
}

async function toggleFileEnabled(file) {
  if (file.status === 'generating') return
  if (!currentKb.value) return
  const kbId = currentKb.value.id
  const nextStatusStr = file.status === 'disabled' ? 'available' : 'disabled'
  const nextStatusInt = nextStatusStr === 'available' ? 1 : 0
  try {
    await ragStore.updateFileStatusInKb({
      kbId,
      fileId: file.id,
      status: nextStatusInt
    })
    file.status = nextStatusStr
  } catch (error) {
    console.error(t('rag.toggleFileStatusFailed', { error: error.message }), error)
    alert(t('rag.toggleFileStatusFailed', { error: error.message || t('common.unknown') }))
  }
}

async function deleteFile(file) {
  if (!currentKb.value) return
  if (!confirm(t('common.confirmDelete'))) return
  const kbId = currentKb.value.id
  try {
    await ragStore.deleteKbFile({
      kbId,
      fileId: file.id
    })
    fileList.value = fileList.value.filter((f) => f.id !== file.id)
  } catch (error) {
    console.error('Failed to delete file:', error)
    alert(`${t('common.delete')} ${t('common.error')}: ${error.message || t('common.unknown')}`)
  }
}

async function downloadFile(file) {
  if (!currentKb.value) return
  const kbId = currentKb.value.id
  try {
    const response = await ragApi.getFileDownloadUrl({
      kb_id: kbId,
      file_id: file.id
    })
    const data = response?.data?.data || {}
    const url = data.url
    if (!url) {
      alert(t('rag.downloadTip'))
      return
    }
    const a = document.createElement('a')
    a.href = url
    a.download = file.name || data.file_name || ''
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } catch (error) {
    console.error('Failed to get download URL:', error)
    alert(`${t('rag.download')} ${t('common.error')}: ${error.message || t('common.unknown')}`)
  }
}

async function remove(item) {
  if (!confirm(t('rag.confirmDelete', { name: item.name }))) return
  try {
    await ragStore.deleteKnowledgeBase(item.id)
  } catch (error) {
    console.error('Failed to delete KB:', error)
    alert(`${t('common.delete')} ${t('common.error')}: ${error.message || t('common.unknown')}`)
  }
}

async function exportKnowledge(item) {
  try {
    const data = await ragStore.exportKnowledgeBase(item.id)
    if (!data) {
      alert(t('rag.export') + ' ' + t('common.error'))
      return
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json;charset=utf-8'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${item.name || 'knowledge-base'}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export KB:', error)
    alert(`${t('rag.export')} ${t('common.error')}: ${error.message || t('common.unknown')}`)
  }
}

async function toggleEnabled(item) {
  const targetStatus = item.status === 'enabled' ? 'disabled' : 'enabled'
  try {
    await ragStore.updateKnowledgeBase({
      id: item.id,
      status: targetStatus
    })
  } catch (error) {
    console.error('Failed to toggle KB status:', error)
    alert(`${t('rag.segment.status')} ${t('common.error')}: ${error.message || t('common.unknown')}`)
  }
}

function typeLabel(type) {
  return t(`rag.types.${type}`)
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '0 KB'
  const kb = bytes / 1024
  if (kb < 1) {
    return (bytes / 1024).toFixed(2) + ' KB'
  }
  if (kb < 1024) {
    return kb.toFixed(2) + ' KB'
  }
  const mb = kb / 1024
  if (mb < 1024) {
    return mb.toFixed(2) + ' MB'
  }
  const gb = mb / 1024
  return gb.toFixed(2) + ' GB'
}

const showDetail = ref(false)
const isSegmentView = ref(false)
const detailFile = ref(null)
const segments = ref([])
const segmentSort = ref('default')

async function fetchSegments() {
  if (!detailFile.value) return
  
  let sortBy = null
  let sortOrder = 'desc'
  
  if (segmentSort.value === 'recall_desc') {
    sortBy = 'recall_count'
    sortOrder = 'desc'
  } else if (segmentSort.value === 'recall_asc') {
    sortBy = 'recall_count'
    sortOrder = 'asc'
  } else if (segmentSort.value === 'updated_desc') {
    sortBy = 'updated_at'
    sortOrder = 'desc'
  }
  
  try {
    segments.value = await ragStore.fetchKnowledgeSegments({
      fileId: detailFile.value.id,
      pageNo: 1,
      pageSize: 50,
      sortBy,
      sortOrder
    })
  } catch (e) {
    segments.value = []
  }
}

async function onSegmentSortChange() {
  await fetchSegments()
}

async function openKnowledgeDetail(item) {
  detailFile.value = item
  isSegmentView.value = true
  segmentSort.value = 'default'
  await fetchSegments()
}

function closeKnowledgeDetail() {
  isSegmentView.value = false
  detailFile.value = null
  segments.value = []
}

// 编辑相关逻辑
const showEdit = ref(false)
const saving = ref(false)
const editForm = ref({
  id: null,
  title: '',
  content: '',
  status: 1
})

function openEdit(seg) {
  editForm.value = {
    id: seg.id,
    title: seg.title || '',
    content: seg.content || '',
    status: seg.status ?? 1
  }
  showEdit.value = true
}

function openCreate() {
  editForm.value = {
    id: null,
    title: '',
    content: '',
    status: 2 // 默认为启用
  }
  showEdit.value = true
}

function cancelEdit() {
  showEdit.value = false
  editForm.value = { id: null, title: '', content: '', status: 1 }
}

async function saveEdit() {
  if (!editForm.value.content.trim()) {
    alert(t('rag.contentCannotBeEmpty'))
    return
  }
  
  saving.value = true
  try {
    if (editForm.value.id) {
      // 更新
      await ragStore.updateKnowledgeSegment(editForm.value)
      
      // 更新本地列表数据
      const index = segments.value.findIndex(s => s.id === editForm.value.id)
      if (index !== -1) {
        segments.value[index] = {
          ...segments.value[index],
          ...editForm.value,
          updated_at: new Date().toISOString()
        }
      }
    } else {
      // 创建
      if (!detailFile.value) {
        throw new Error(t('rag.fileInfoNotFound'))
      }
      const newSeg = await ragStore.createKnowledgeSegment({
        ...editForm.value,
        file_id: detailFile.value.id
      })
      
      // 添加到本地列表（插在最前）
      // newSeg 应该包含 id
      if (newSeg && newSeg.id) {
        segments.value.unshift({
          ...editForm.value,
          id: newSeg.id,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          snippet_type: 'text'
        })
      }
    }
    
    showEdit.value = false
  } catch (error) {
    console.error(t('rag.saveFailed', { error }), error)
    alert(`${t('common.save')} ${t('common.error')}: ${error.message || 'Unknown error'}`)
  } finally {
    saving.value = false
  }
}

function getStatusText(status) {
  const map = {
    0: t('rag.segment.statusMap.disabled'),
    1: t('rag.segment.statusMap.draft'),
    2: t('rag.segment.statusMap.enabled')
  }
  return map[status] ?? t('common.unknown')
}

function getStatusClass(status) {
  const map = {
    0: 'status-disabled',
    1: 'status-draft',
    2: 'status-enabled'
  }
  return map[status] ?? ''
}

async function deleteSegment(seg) {
  if (!confirm(t('rag.segment.deleteConfirm'))) return
  try {
    await ragStore.deleteKnowledgeSegment(seg.id)
    // 更新本地列表数据
    segments.value = segments.value.filter(s => s.id !== seg.id)
  } catch (error) {
    console.error(t('rag.segment.deleteFailed', { error }), error)
    alert(`${t('common.delete')} ${t('common.error')}: ${error.message || 'Unknown error'}`)
  }
}

async function toggleSegmentStatus(seg) {
  const nextStatus = seg.status === 2 ? 0 : 2 // 2=启用, 0=禁用 (假设1是草稿)
  try {
    await ragStore.updateKnowledgeSegment({
      id: seg.id,
      status: nextStatus
    })
    seg.status = nextStatus
  } catch (error) {
    console.error(t('rag.segment.updateStatusFailed', { error }), error)
    alert(`${t('rag.segment.status')} ${t('common.error')}: ${error.message || 'Unknown error'}`)
  }
}
</script>

<template>
  <div class="rag-mng">
    <!-- 编辑/新建弹窗 -->
    <Teleport to="body">
      <div v-if="showEdit" class="kb-detail-overlay" @click.self="cancelEdit">
        <div class="kb-detail-modal edit-modal">
          <div class="kb-detail-header">
            <div class="kb-detail-title">{{ editForm.id ? t('rag.segment.titleEdit') : t('rag.segment.titleAdd') }}</div>
            <button type="button" class="btn-secondary" @click="cancelEdit">{{ t('rag.ontology.edit.close') }}</button>
          </div>
          <div class="kb-detail-body edit-body">
            <div class="form-item">
              <label>{{ t('rag.segment.title') }}</label>
              <input v-model="editForm.title" type="text" :placeholder="t('rag.segment.titlePlaceholder')" />
            </div>
            <div class="form-item">
              <label>{{ t('rag.segment.status') }}</label>
              <select v-model="editForm.status">
                <option :value="0">{{ t('rag.segment.statusMap.disabled') }}</option>
                <option :value="1">{{ t('rag.segment.statusMap.draft') }}</option>
                <option :value="2">{{ t('rag.segment.statusMap.enabled') }}</option>
              </select>
            </div>
            <div class="form-item flex-1">
              <label>{{ t('rag.segment.content') }}</label>
              <textarea v-model="editForm.content" :placeholder="t('rag.segment.contentPlaceholder')"></textarea>
            </div>
          </div>
          <div class="kb-detail-footer">
            <button type="button" class="btn-secondary" @click="cancelEdit">{{ t('rag.ontology.edit.cancel') }}</button>
            <button type="button" class="btn-primary" :disabled="saving" @click="saveEdit">
              {{ saving ? t('rag.ontology.edit.saving') : t('rag.ontology.edit.save') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Ontology Edit Modal -->
      <div v-if="showOntologyEdit" class="kb-detail-overlay" @click.self="cancelOntologyEdit">
        <div class="kb-detail-modal edit-modal">
          <div class="kb-detail-header">
            <div class="kb-detail-title">{{ ontologyForm.id ? t('rag.ontology.edit.titleEdit') : t('rag.ontology.edit.titleAdd') }}</div>
            <button type="button" class="btn-secondary" @click="cancelOntologyEdit">{{ t('rag.ontology.edit.close') }}</button>
          </div>
          <div class="kb-detail-body edit-body">
            <div class="form-item">
              <label>{{ t('rag.ontology.edit.name') }}</label>
              <input v-model="ontologyForm.name" type="text" :placeholder="t('rag.ontology.edit.namePlaceholder')" />
            </div>
            <div class="form-item">
              <label>{{ t('rag.ontology.edit.label') }}</label>
              <input v-model="ontologyForm.label" type="text" :placeholder="t('rag.ontology.edit.labelPlaceholder')" :disabled="!!ontologyForm.id" />
              <small class="form-tip" v-if="ontologyForm.id">{{ t('rag.ontology.edit.labelTip') }}</small>
            </div>
            <div class="form-item flex-1">
              <label>{{ t('rag.ontology.edit.properties') }}</label>
              <textarea v-model="ontologyForm.properties" placeholder='{ "key": "value" }' class="code-textarea"></textarea>
            </div>
          </div>
          <div class="kb-detail-footer">
            <button type="button" class="btn-secondary" @click="cancelOntologyEdit">{{ t('rag.ontology.edit.cancel') }}</button>
            <button type="button" class="btn-primary" :disabled="isOntologySaving" @click="saveOntologyNode">
              {{ isOntologySaving ? t('rag.ontology.edit.saving') : t('rag.ontology.edit.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <div class="rag-header">
      <!-- Ontology Stats (Always visible or only when relevant?) -->
      <div class="ontology-stats-bar" v-if="!isFileView">
        <div class="stat-item">
          <span class="stat-label">{{ t('rag.ontology.nodes') }}</span>
          <span class="stat-val">{{ ontologyStats.total_nodes || 0 }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">{{ t('rag.ontology.relations') }}</span>
          <span class="stat-val">{{ ontologyStats.total_relations || 0 }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">{{ t('rag.ontology.types') }}</span>
          <span class="stat-val">{{ Object.keys(ontologyStats.labels || {}).length }}</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-label">{{ t('rag.ontology.recall') }}</span>
          <span class="stat-val">{{ ontologyStats.total_recall_count || 0 }}</span>
        </div>
      </div>

      <div class="rag-desc-wrap">
        <button
          v-if="isFileView"
          type="button"
          class="btn-secondary rag-back-btn"
          :aria-label="t('rag.backToKb')"
          @click="backToKbList"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="9" />
            <polyline points="13.5 8 9.5 12 13.5 16" />
            <line x1="15" y1="12" x2="9.5" y2="12" />
          </svg>
        </button>
        <span class="rag-desc-icon" aria-hidden="true">ℹ</span>
        <span class="rag-desc">{{ t('rag.fileSupportDesc') }}</span>
      </div>
    </div>

    <div class="rag-table-wrap" v-if="!isFileView">
      <!-- Ontology Filter Bar -->
      <div class="ontology-filter-bar">
        <div class="filter-group">
          <span class="filter-label">{{ t('rag.ontology.filter') }}:</span>
          <select v-model="selectedOntology" class="ontology-select">
            <option v-for="opt in ontologyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
          <div class="search-input-wrap">
            <input v-model="ontologySearchQuery" type="text" :placeholder="t('rag.ontology.searchPlaceholder')" class="ontology-search" />
          </div>
        </div>
        <div class="filter-actions">
           <button class="btn-secondary btn-sm" @click="handleAddOntology">
             <span class="icon">+</span> {{ t('rag.ontology.add') }}
           </button>
           <button class="btn-secondary btn-sm" @click="handleBatchTag">
             <span class="icon">🏷️</span> {{ t('rag.ontology.batchTag') }}
           </button>
        </div>
      </div>

      <div v-if="loading || isOntologyLoading" class="rag-loading">{{ t('common.loading') }}</div>
      
      <!-- Ontology Node Table -->
      <table v-else-if="isOntologyViewMode" class="rag-table rag-ontology-table">
        <thead>
          <tr>
            <th>{{ t('rag.ontology.columns.id') }}</th>
            <th>{{ t('rag.ontology.columns.name') }}</th>
            <th>{{ t('rag.ontology.columns.type') }}</th>
            <th>{{ t('rag.ontology.columns.properties') }}</th>
            <th>{{ t('rag.ontology.columns.updatedAt') }}</th>
            <th class="col-actions">{{ t('rag.ontology.columns.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredList.length === 0">
            <td colspan="6" class="empty-col">{{ t('common.noData') }}</td>
          </tr>
          <tr v-for="node in filteredList" :key="node.internal_id">
            <td class="col-id" :title="node.id">{{ node.id }}</td>
            <td class="col-name">{{ node.name }}</td>
            <td>
              <span v-for="lbl in node.labels" :key="lbl" class="ontology-tag">{{ lbl }}</span>
            </td>
            <td class="col-props">
              <span class="props-summary" :title="JSON.stringify(node.properties, null, 2)">
                {{ Object.keys(node.properties).filter(k => !['id','name','created_at','updated_at'].includes(k)).join(', ') || '-' }}
              </span>
            </td>
            <td>{{ formatTime(node.updated_at || node.created_at) }}</td>
            <td class="col-actions">
              <div class="action-group">
                <button class="action-btn" :title="t('common.edit')" @click.stop="handleEditOntology(node)">
                  <span class="action-text">{{ t('common.edit') }}</span>
                </button>
                <button class="action-btn text-danger" :title="t('common.delete')" @click.stop="handleDeleteOntology(node)">
                  <span class="action-text">{{ t('common.delete') }}</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Knowledge Base Table -->
      <table v-else class="rag-table rag-kb-table">
        <thead>
          <tr>
            <th>{{ t('rag.columns.name') }}</th>
            <th>{{ t('rag.columns.updatedAt') }}</th>
            <th>{{ t('rag.columns.createdAt') }}</th>
            <th>{{ t('rag.columns.status') }}</th>
            <th>{{ t('rag.columns.totalCapacity') }}</th>
            <th>{{ t('rag.columns.fileCount') }}</th>
            <th class="kb-col-actions">{{ t('rag.columns.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredList.length === 0">
            <td colspan="6" class="empty-cell">{{ t('common.noData') }}</td>
          </tr>
          <tr v-for="item in filteredList" :key="item.id">
            <td class="col-name">
              <div class="kb-name-wrap">
                <div class="kb-name-text">{{ item.name }}</div>
              </div>
            </td>
            <td class="col-time">{{ formatTime(item.updated_at) }}</td>
            <td class="col-time">{{ formatTime(item.created_at) }}</td>
            <td class="col-status">
              <div class="status-wrap">
                <span
                  class="status-pill"
                  :class="{
                    enabled: item.status === 'enabled',
                    generating: item.status === 'generating',
                    disabled: item.status === 'disabled'
                  }"
                >
                  {{
                    item.status === 'enabled'
                      ? t('rag.statusEnabled')
                      : item.status === 'generating'
                      ? t('rag.statusGenerating')
                      : t('rag.statusDisabled')
                  }}
                </span>
              </div>
            </td>
            <td class="col-capacity">{{ formatFileSize(item.file_capacity) }}</td>
            <td class="col-count">{{ item.file_count ?? 0 }}</td>
            <td class="kb-col-actions">
              <div class="action-group">
                <!-- 查看文件按钮 -->
                <button type="button" class="action-btn" :title="t('rag.viewFiles')" @click="openFileView(item)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span class="action-text">{{ t('rag.viewFiles') }}</span>
                </button>

                <!-- 查看知识按钮：跳转到对话页 -->
                <button
                  type="button"
                  class="action-btn"
                  :title="t('rag.viewKnowledge')"
                  @click="viewKnowledge(item)"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M4 4.5A2.5 2.5 0 0 0 6.5 7H20" />
                    <path d="M6.5 17V7" />
                    <path d="M20 22V2" />
                  </svg>
                  <span class="action-text">{{ t('rag.viewKnowledge') }}</span>
                </button>

                <!-- 正在生成：只允许查看和删除 -->
                <template v-if="item.status === 'generating'">
                  <button type="button" class="action-btn danger" :title="t('common.delete')" @click="remove(item)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                    <span class="action-text">{{ t('common.delete') }}</span>
                  </button>
                </template>

                <!-- 其他状态：导出 + 启用/禁用 + 删除 -->
                <template v-else>
                  <button type="button" class="action-btn" :title="t('rag.export')" @click="exportKnowledge(item)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <span class="action-text">{{ t('rag.export') }}</span>
                  </button>
                  <button
                    type="button"
                    class="action-btn"
                    :title="item.status === 'enabled' ? t('rag.disable') : t('rag.enable')"
                    @click="toggleEnabled(item)"
                  >
                    <svg v-if="item.status === 'enabled'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path
                        d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"
                      />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                    <span class="action-text">{{ item.status === 'enabled' ? t('rag.disable') : t('rag.enable') }}</span>
                  </button>
                  <button type="button" class="action-btn danger" :title="t('common.delete')" @click="remove(item)">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                    <span class="action-text">{{ t('common.delete') }}</span>
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <div class="rag-pagination" v-if="!isFileView">
        <!-- Ontology Pagination -->
        <div v-if="isOntologyViewMode" class="pagination-wrap">
          <button 
            class="page-btn" 
            :disabled="ontologyPagination.page <= 1"
            @click="handleOntologyPageChange(ontologyPagination.page - 1)"
          >
            &lt;
          </button>
          <span class="page-info">
            {{ ontologyPagination.page }} / {{ Math.ceil(ontologyPagination.total / ontologyPagination.pageSize) || 1 }}
          </span>
          <button 
            class="page-btn" 
            :disabled="ontologyPagination.page >= Math.ceil(ontologyPagination.total / ontologyPagination.pageSize)"
            @click="handleOntologyPageChange(ontologyPagination.page + 1)"
          >
            &gt;
          </button>
        </div>

        <!-- KB Pagination -->
        <div v-else class="pagination-wrap">
          <button 
            class="page-btn" 
            :disabled="pagination.page <= 1"
            @click="handlePageChange(pagination.page - 1)"
          >
            &lt;
          </button>
          <span class="page-info">
            {{ pagination.page }} / {{ Math.ceil(pagination.total / pagination.pageSize) || 1 }}
          </span>
          <button 
            class="page-btn" 
            :disabled="pagination.page >= Math.ceil(pagination.total / pagination.pageSize)"
            @click="handlePageChange(pagination.page + 1)"
          >
            &gt;
          </button>
        </div>
      </div>
    </div>

    <div v-else class="rag-table-wrap">
      <template v-if="activeDetailTab === 'file'">
        <table class="rag-table rag-file-table">
          <thead>
            <tr>
              <th>{{ t('rag.fileColumns.name') }}</th>
              <th>{{ t('rag.fileColumns.status') }}</th>
              <th>{{ t('rag.fileColumns.recallCount') }}</th>
              <th>{{ t('rag.fileColumns.charCount') }}</th>
              <th>{{ t('rag.fileColumns.uploadTime') }}</th>
              <th>{{ t('rag.fileColumns.segmentModel') }}</th>
              <th class="file-col-actions">{{ t('rag.fileColumns.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="fileList.length === 0">
              <td colspan="7" class="empty-cell">{{ t('common.noData') }}</td>
            </tr>
            <tr v-for="file in fileList" :key="file.id">
              <td class="col-name">{{ file.name }}</td>
              <td>
                <span
                  class="status-pill"
                  :class="{
                    enabled: file.status === 'available',
                    generating: file.status === 'generating',
                    disabled: file.status === 'disabled'
                  }"
                >
                  <template v-if="file.status === 'generating'">
                    {{ t('rag.fileStatusGenerating') }}
                    <span v-if="file.progress !== undefined" class="status-progress">
                      {{ file.progress }}%
                    </span>
                  </template>
                  <template v-else>
                    {{
                      file.status === 'available'
                        ? t('rag.fileStatusAvailable')
                        : t('rag.fileStatusDisabled')
                    }}
                  </template>
                </span>
              </td>
              <td>{{ file.recallCount ?? 0 }}</td>
              <td>{{ file.charCount ?? 0 }}</td>
              <td class="col-time">{{ file.uploadTime }}</td>
              <td>{{ file.segmentModel }}</td>
              <td class="file-col-actions">
                <div class="action-group">
                  <button
                    type="button"
                    class="action-btn"
                    :disabled="file.status === 'generating'"
                    @click="toggleFileEnabled(file)"
                  >
                    <span class="action-text">
                      {{
                        file.status === 'disabled'
                          ? t('rag.enable')
                          : t('rag.disable')
                      }}
                    </span>
                  </button>
                  <button
                    type="button"
                    class="action-btn danger"
                    :disabled="file.status === 'generating'"
                    @click="deleteFile(file)"
                  >
                    <span class="action-text">{{ t('common.delete') }}</span>
                  </button>
                  <button
                    type="button"
                    class="action-btn"
                    :disabled="file.status === 'generating'"
                    @click="downloadFile(file)"
                  >
                    <span class="action-text">{{ t('rag.download') }}</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </template>
      <template v-else>
        <!-- 知识片段列表视图 -->
        <template v-if="isSegmentView">
          <div class="rag-files-header">
            <div class="rag-files-title">
              <button
                type="button"
                class="btn-secondary rag-back-btn"
                @click="closeKnowledgeDetail"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="9" />
                  <polyline points="13.5 8 9.5 12 13.5 16" />
                  <line x1="15" y1="12" x2="9.5" y2="12" />
                </svg>
              </button>
              <span class="rag-files-title-text">{{ detailFile?.fileName || t('rag.knowledgeInfo.title') }}</span>
              <span class="rag-files-recall-count" v-if="detailFile?.recallCount !== undefined">
                ({{ t('rag.segment.columns.recallCount') }}: {{ detailFile.recallCount }})
              </span>
            </div>
            <div class="header-actions">
              <select v-model="segmentSort" class="rag-sort-select" @change="onSegmentSortChange">
                <option value="default">{{ t('rag.segment.sort.default') }}</option>
                <option value="recall_desc">{{ t('rag.segment.sort.recall_desc') }}</option>
                <option value="recall_asc">{{ t('rag.segment.sort.recall_asc') }}</option>
                <option value="updated_desc">{{ t('rag.segment.sort.updated_desc') }}</option>
              </select>
              <button type="button" class="btn-primary btn-sm" @click="openCreate">{{ t('rag.segment.titleAdd') }}</button>
            </div>
          </div>

          <table class="rag-table">
            <thead>
              <tr>
                <th style="width: 50%">{{ t('rag.segment.columns.nameContent') }}</th>
                <th>{{ t('rag.segment.columns.recallCount') }}</th>
                <th>{{ t('rag.segment.columns.status') }}</th>
                <th>{{ t('rag.segment.columns.updatedAt') }}</th>
                <th class="knowledge-col-actions">{{ t('rag.segment.columns.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="segments.length === 0">
                <td colspan="5" class="empty-cell">{{ t('rag.segment.empty') }}</td>
              </tr>
              <tr v-for="seg in segments" :key="seg.id">
                <td class="col-name" :title="seg.content">
                  <div class="text-truncate">{{ seg.title || seg.content || seg.summary || t('rag.segment.noContent') }}</div>
                </td>
                <td>{{ seg.recall_count ?? 0 }}</td>
                <td>
                  <span
                    class="status-pill"
                    :class="getStatusClass(seg.status)"
                  >
                    {{ getStatusText(seg.status) }}
                  </span>
                </td>
                <td class="col-time">{{ formatTime(seg.updated_at || seg.created_at) }}</td>
                <td class="knowledge-col-actions">
                  <div class="action-group">
                    <button
                      type="button"
                      class="action-btn"
                      @click="toggleSegmentStatus(seg)"
                      :title="seg.status === 2 ? t('rag.disable') : t('rag.enable')"
                    >
                      <span class="action-text">{{ seg.status === 2 ? t('rag.disable') : t('rag.enable') }}</span>
                    </button>
                    <button type="button" class="action-btn" @click="openEdit(seg)">
                      <span class="action-text">{{ t('common.edit') }}</span>
                    </button>
                    <button type="button" class="action-btn danger" @click="deleteSegment(seg)">
                      <span class="action-text">{{ t('common.delete') }}</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </template>

        <!-- 知识列表视图 -->
        <template v-else>
          <div class="rag-files-header">
            <div class="rag-files-title">
              <span class="rag-files-title-text">{{ t('rag.knowledgeInfo.title') }}</span>
              <div class="rag-knowledge-filters">
                <label>
                  {{ t('rag.knowledgeInfo.filter.time') }}
                  <select v-model="knowledgeTimeFilter" @change="onKnowledgeFilterChange">
                    <option value="all">{{ t('rag.knowledgeInfo.options.all') }}</option>
                    <option value="last7d">{{ t('rag.knowledgeInfo.options.last7d') }}</option>
                    <option value="last30d">{{ t('rag.knowledgeInfo.options.last30d') }}</option>
                    <option value="last90d">{{ t('rag.knowledgeInfo.options.last90d') }}</option>
                  </select>
                </label>
                <label>
                  {{ t('rag.knowledgeInfo.filter.recall') }}
                  <select v-model="knowledgeRecallFilter" @change="onKnowledgeFilterChange">
                    <option value="all">{{ t('rag.knowledgeInfo.options.all') }}</option>
                    <option value="never">{{ t('rag.knowledgeInfo.options.never') }}</option>
                    <option value="has">{{ t('rag.knowledgeInfo.options.has') }}</option>
                  </select>
                </label>
                <label>
                  {{ t('rag.knowledgeInfo.filter.sort') }}
                  <select v-model="knowledgeSort" @change="onKnowledgeFilterChange">
                    <option value="recall_desc">{{ t('rag.knowledgeInfo.options.recallDesc') }}</option>
                    <option value="recall_asc">{{ t('rag.knowledgeInfo.options.recallAsc') }}</option>
                    <option value="time_desc">{{ t('rag.knowledgeInfo.options.timeDesc') }}</option>
                    <option value="time_asc">{{ t('rag.knowledgeInfo.options.timeAsc') }}</option>
                  </select>
                </label>
              </div>
            </div>
          </div>
          <table class="rag-table">
            <thead>
              <tr>
                <th>{{ t('rag.knowledgeInfo.columns.fileName') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.recallCount') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.lastAccess') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.avgScore') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.instructionScore') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.relevanceScore') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.isNoise') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.isRedundant') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.createdAt') }}</th>
                <th>{{ t('rag.knowledgeInfo.columns.updatedAt') }}</th>
                <th class="knowledge-col-actions">{{ t('rag.knowledgeInfo.columns.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="knowledgeList.length === 0">
                <td colspan="11" class="empty-cell">{{ t('rag.knowledgeInfo.empty') }}</td>
              </tr>
              <tr
                v-for="item in knowledgeList"
                :key="item.id ?? `${item.fileName}-${item.createdAt}`"
              >
                <td class="col-name">{{ item.fileName || '-' }}</td>
                <td>{{ item.recallCount ?? 0 }}</td>
                <td>{{ item.lastAccessTime || '-' }}</td>
                <td>{{ item.avgScore ?? '-' }}</td>
                <td>{{ item.instructionScore ?? '-' }}</td>
                <td>{{ item.relevanceScore ?? '-' }}</td>
                <td>{{ item.isNoise ? t('rag.knowledgeInfo.yes') : t('rag.knowledgeInfo.no') }}</td>
                <td>{{ item.isRedundant ? t('rag.knowledgeInfo.yes') : t('rag.knowledgeInfo.no') }}</td>
                <td>{{ item.createdAt || '-' }}</td>
                <td>{{ item.updatedAt || '-' }}</td>
                <td class="knowledge-col-actions">
                  <div class="action-group">
                    <button type="button" class="action-btn" @click="openKnowledgeDetail(item)">
                      <span class="action-text">{{ t('rag.view') }}</span>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </template>
      </template>
    </div>
  </div>
</template>



<style scoped lang="scss">
.rag-mng {
  min-height: 200px;
}

.rag-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.rag-desc-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  padding: 10px 14px;
  background: rgba(var(--accent-rgb, 34 197 94), 0.08);
  border: 1px solid rgba(var(--accent-rgb, 34 197 94), 0.2);
  border-radius: 10px;
}

.rag-desc-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.16);
  color: #22c55e;
  font-size: 0.8rem;
}

.rag-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.btn-secondary {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.rag-table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.kb-detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.kb-detail-modal {
  width: 820px;
  max-height: 80vh;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.kb-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rag-sort-select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.85rem;
  min-width: 140px;
  cursor: pointer;

  &:focus {
    border-color: var(--accent-color, #22c55e);
    outline: none;
  }
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.8rem;
}

.kb-detail-title {
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
}

.kb-detail-body {
  padding: 12px 16px;
  overflow: auto;
}

.segment-list {
  display: grid;
  gap: 10px;
}

.segment-card {
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  padding: 12px;
  background: var(--bg-tertiary);
}

.segment-title {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.segment-meta {
  margin-left: 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.segment-summary {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.segment-empty {
  color: var(--text-secondary);
  padding: 16px 8px;
}


.rag-loading {
  padding: 40px 24px;
  text-align: center;
  font-size: 0.9rem;
}

/* Ontology Stats Bar */
.ontology-stats-bar {
  display: flex;
  align-items: center;
  gap: 32px;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 8px 24px;
  margin-bottom: 0;
  flex: 1;
  height: 46px; /* Match height of other headers if needed */
}

.stat-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.stat-val {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.stat-divider {
  width: 1px;
  height: 16px;
  background-color: var(--border-primary);
}

/* Ontology Filter Bar */
.ontology-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.ontology-select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  min-width: 200px;
}

.search-input-wrap {
  position: relative;
}

.ontology-search {
  padding: 6px 12px;
  padding-left: 30px; /* space for icon if added */
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  width: 240px;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

/* Ontology Table Styles */
.rag-ontology-table .ontology-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: rgba(var(--primary-rgb), 0.1);
  color: var(--primary);
  font-size: 12px;
  margin-right: 4px;
  border: 1px solid rgba(var(--primary-rgb), 0.2);
}

.rag-ontology-table .props-summary {
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}

.rag-ontology-table .col-id {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rag-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.rag-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.rag-table th,
.rag-table td {
  padding: 10px 14px;
  text-align: left;
}

.rag-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.rag-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.rag-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.kb-col-actions {
  width: 480px;
}

.file-col-actions {
  width: 300px;
}

.knowledge-col-actions {
  width: 240px;
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px 12px;
}

.action-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-right: 6px;

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    border-color: var(--border-primary);
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.danger:hover {
    border-color: rgba(248, 113, 113, 0.6);
    color: #f97373;
  }
}

.col-name {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-time,
.col-capacity,
.col-count {
  white-space: nowrap;
}

.status-progress {
  margin-left: 4px;
  font-size: 0.8em;
  opacity: 0.85;
}

.rag-files-header {
  padding: 12px 16px 0;
}

.rag-files-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.rag-files-title-text {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.rag-files-recall-count {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-left: 4px;
}

.rag-back-btn {
  padding: 4px;

  svg {
    width: 22px;
    height: 22px;
  }
}

.rag-knowledge-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-left: auto;
}

.rag-knowledge-filters select {
  margin-left: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 0.8rem;
}

.rag-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding: 0 16px 16px;
}

.pagination-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-secondary);
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
}

.page-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover:not(:disabled) {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-color: var(--border-primary);
  }
  
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.page-info {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  padding: 0 8px;
}

.segment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.segment-status {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-disabled {
  background: rgba(var(--text-secondary-rgb, 156 163 175), 0.1);
  color: var(--text-secondary);
}

.status-draft {
  background: rgba(var(--accent-rgb, 34 197 94), 0.1);
  color: #fbbf24;
}

.status-enabled {
  background: rgba(var(--accent-rgb, 34 197 94), 0.1);
  color: #22c55e;
}

.segment-footer {
  margin-top: 8px;
  text-align: right;
}

.btn-text {
  background: none;
  border: none;
  color: var(--accent-color, #22c55e);
  cursor: pointer;
  font-size: 0.85rem;
  padding: 4px 8px;
  
  &:hover {
    text-decoration: underline;
  }
}

.btn-text.danger {
  color: #ef4444;
  
  &:hover {
    color: #dc2626;
  }
}

.edit-modal {
  width: 600px;
  height: 600px;
}

.edit-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  
  label {
    font-size: 0.9rem;
    color: var(--text-secondary);
  }
  
  input, select, textarea {
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid var(--border-primary);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: 0.9rem;
    
    &:focus {
      outline: none;
      border-color: var(--accent-color, #22c55e);
    }
  }
  
  textarea {
    flex: 1;
    resize: none;
    min-height: 200px;
  }
}

.flex-1 {
  flex: 1;
  min-height: 0;
}

.kb-detail-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 14px 16px;
  border-top: 1px solid var(--border-primary);
}

.btn-primary {
  padding: 8px 16px;
  border-radius: 999px;
  border: none;
  background: var(--accent-color, #22c55e);
  color: #fff;
  font-size: 0.85rem;
  cursor: pointer;
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

/* Ontology Styles */
.ontology-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.ontology-select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.85rem;
  min-width: 160px;
  cursor: pointer;
  
  &:focus {
    border-color: var(--accent-color, #22c55e);
    outline: none;
  }
}

.search-input-wrap {
  position: relative;
}

.ontology-search {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.85rem;
  width: 200px;
  
  &:focus {
    border-color: var(--accent-color, #22c55e);
    outline: none;
  }
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.8rem;
  gap: 6px;
}

.kb-name-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.kb-name-text {
  font-weight: 500;
  color: var(--text-primary);
}

.ontology-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
}

.ontology-tag {
  color: var(--accent-color, #22c55e);
  background: rgba(var(--accent-rgb, 34 197 94), 0.1);
  padding: 1px 6px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  white-space: nowrap;
}

.ontology-props-preview {
  color: var(--text-muted);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.status-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ontology-version-icon {
  font-size: 0.75rem;
  color: var(--text-muted);
  cursor: help;
  opacity: 0.7;
  
  &:hover {
    opacity: 1;
    color: var(--text-secondary);
  }
}

.col-actions {
  width: 140px;
}

.text-danger {
  color: #ef4444;
  
  &:hover {
    color: #dc2626;
  }
}

.code-textarea {
  font-family: 'Fira Code', monospace;
  font-size: 0.85rem;
  line-height: 1.5;
}

.form-tip {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rag-sort-select {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.85rem;
  min-width: 140px;
  cursor: pointer;
}

.rag-sort-select:focus {
  border-color: var(--accent-color, #22c55e);
  outline: none;
}
</style>
