<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { mcpToolsApi } from '@/api/mcpTools'

const { t } = useI18n()

const toolList = ref([])
const discoveredTools = ref([])
const loading = ref(false)
const keyword = ref('')
const selectedIds = ref([])
const viewMode = ref('list')
const formMode = ref('create')
const formType = ref('hardware')
const formPath = ref('')
const formName = ref('')
const formDesc = ref('')
const selectedServerId = ref(null)
const endpointUrl = ref('')
const apiKey = ref('')
const serverList = ref([])
const editingItem = ref(null)
const showDetailList = ref(false)
const showAddServer = ref(false)
const newServerName = ref('')
const newServerUrl = ref('')
const newServerApiKey = ref('')

const viewingItem = ref(null)
const showViewModal = ref(false)

const TOOL_TYPES = {
  smartDevice: 'mcp.toolTypes.smartDevice',
  virtualDevice: 'mcp.toolTypes.virtualDevice',
  function: 'mcp.toolTypes.function',
  // Map backend types
  service: 'mcp.toolTypes.service',
  device: 'mcp.toolTypes.smartDevice'
}

async function fetchServers() {
  try {
    const res = await mcpToolsApi.getServerList({ page: 1, page_size: 100 })
    if (res.data && res.data.data && res.data.data.items) {
      serverList.value = res.data.data.items.map(item => ({
        id: item.id,
        name: item.name,
        baseUrl: item.base_url
      }))
    }
  } catch (error) {
    console.error('Failed to load MCP servers:', error)
  }
}

async function fetchTools() {
  loading.value = true
  try {
    const res = await mcpToolsApi.getToolList({ page: 1, page_size: 100 })
    if (res.data && res.data.data && res.data.data.items) {
      toolList.value = res.data.data.items.map(item => ({
        id: item.id,
        name: item.name || item.display_name,
        type: item.tool_type, // 'function', 'service', 'device'
        registeredAt: item.created_at ? new Date(item.created_at).toLocaleString() : '-',
        updatedAt: item.updated_at ? new Date(item.updated_at).toLocaleString() : '-',
        description: item.description_short || item.description_full || item.description,
        server_id: item.server_id,
        endpoint_url: item.endpoint_url // Assuming backend returns this if we need to edit
      }))
    } else {
      toolList.value = []
    }
  } catch (error) {
    console.error('Failed to load MCP tools:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchTools()
  fetchServers()
})

const filteredList = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return toolList.value
  return toolList.value.filter((item) => item.name.includes(kw))
})

function toolTypeLabel(type) {
  return t(TOOL_TYPES[type] || type)
}

const isAllSelected = computed(
  () =>
    filteredList.value.length > 0 &&
    filteredList.value.every((item) => selectedIds.value.includes(item.id))
)

function toggleRowSelection(id, checked) {
  if (checked) {
    if (!selectedIds.value.includes(id)) {
      selectedIds.value.push(id)
    }
  } else {
    selectedIds.value = selectedIds.value.filter((itemId) => itemId !== id)
  }
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    const idsInView = new Set(filteredList.value.map((item) => item.id))
    selectedIds.value = selectedIds.value.filter((id) => !idsInView.has(id))
  } else {
    const ids = filteredList.value.map((item) => item.id)
    const merged = new Set([...selectedIds.value, ...ids])
    selectedIds.value = Array.from(merged)
  }
}

function isSelected(id) {
  return selectedIds.value.includes(id)
}

function createTool() {
  formMode.value = 'create'
  editingItem.value = null
  formType.value = 'hardware'
  formPath.value = ''
  formName.value = ''
  formDesc.value = ''
  selectedServerId.value = null
  endpointUrl.value = ''
  apiKey.value = ''
  viewMode.value = 'form'
  showDetailList.value = false
}

function viewTool(item) {
  viewingItem.value = item
  showViewModal.value = true
}

function closeViewModal() {
  showViewModal.value = false
  viewingItem.value = null
}

function editTool(item) {
  formMode.value = 'edit'
  editingItem.value = item
  formType.value = item.type === 'smartDevice' ? 'hardware' : 'service'
  formPath.value = '' // Backend doesn't store path yet? Using description or custom field?
  formName.value = item.name
  formDesc.value = item.description
  selectedServerId.value = item.server_id
  endpointUrl.value = item.endpoint_url
  apiKey.value = ''
  viewMode.value = 'form'
  showDetailList.value = false
}

function backToList() {
  viewMode.value = 'list'
  showDetailList.value = false
}

async function viewToolDetail() {
  let targetUrl = ''
  
  if (formType.value === 'service') {
    if (selectedServerId.value) {
       const server = serverList.value.find(s => s.id === selectedServerId.value)
       if (server) targetUrl = server.baseUrl
    } else {
        targetUrl = endpointUrl.value
    }
  } else {
    targetUrl = formPath.value
  }
  
  if (targetUrl && !targetUrl.startsWith('http')) {
      targetUrl = 'http://' + targetUrl
  }
  
  if (!targetUrl) {
     alert('请填写有效的 MCP 服务地址')
     return
  }

  showDetailList.value = true
  discoveredTools.value = []
  loading.value = true
  
  try {
     const res = await mcpToolsApi.discoverTools(targetUrl, apiKey.value)
    const data = res.data
    if (data && (data.code === 0 || data.code === 200)) {
      let items = []
      const rawData = data.data || data.items || data
      
      if (Array.isArray(rawData)) {
        items = rawData
      } else if (rawData && Array.isArray(rawData.items)) {
        items = rawData.items
      }

      if (Array.isArray(items)) {
        discoveredTools.value = items.map(item => ({
          id: item.name, 
          name: item.name,
          type: item.tool_type || 'function',
          description: item.description || item.description_short
        }))
      }
    } else {
      console.error(res)
      alert('获取工具列表失败: ' + (data?.message || 'Unknown error'))
    }
  } catch (e) {
      console.error(e)
      alert('获取工具列表失败')
  } finally {
      loading.value = false
  }
}

async function addMcpServer() {
  if (!newServerName.value || !newServerUrl.value) {
    alert('请填写完整的服务器信息')
    return
  }
  try {
    await mcpToolsApi.addServer({
      server_name: newServerName.value,
      base_url: newServerUrl.value,
      api_key: newServerApiKey.value
    })
    await fetchServers()
    showAddServer.value = false
    newServerName.value = ''
    newServerUrl.value = ''
    newServerApiKey.value = ''
  } catch (error) {
    console.error('Failed to add server:', error)
    alert('添加服务器失败')
  }
}

async function confirmTool() {
  if (!formName.value) {
    alert('请输入工具名称')
    return
  }
  
  if (formType.value === 'service') {
    if (!selectedServerId.value) {
      alert('请选择 MCP 服务器')
      return
    }
    if (!endpointUrl.value) {
      alert('请输入 Endpoint URL')
      return
    }
  }

  const toolData = {
    name: formName.value,
    display_name: formName.value,
    tool_type: formType.value === 'hardware' ? 'device' : 'service',
    description_short: formDesc.value,
    description_full: formPath.value ? `Path: ${formPath.value}\n${formDesc.value}` : formDesc.value,
    server_id: formType.value === 'service' ? selectedServerId.value : null,
    endpoint_url: formType.value === 'service' ? endpointUrl.value : formPath.value,
    api_key: apiKey.value || null
  }

  try {
    if (formMode.value === 'create') {
      await mcpToolsApi.addTool(toolData)
    } else {
      await mcpToolsApi.updateTool({
        id: editingItem.value.id,
        ...toolData
      })
    }
    await fetchTools()
    viewMode.value = 'list'
  } catch (error) {
    console.error('Failed to save tool:', error)
    alert('保存失败')
  }
}

async function removeTool(item) {
  if (!window.confirm(`确认删除工具「${item.name}」吗？`)) return
  try {
    await mcpToolsApi.deleteTool(item.id)
    await fetchTools()
    selectedIds.value = selectedIds.value.filter((id) => id !== item.id)
  } catch (error) {
    console.error('Failed to delete tool:', error)
    alert('删除失败')
  }
}

async function removeSelected() {
  if (selectedIds.value.length === 0) {
    alert('请先选择要删除的工具')
    return
  }
  if (!window.confirm('确认删除选中的工具吗？')) return
  
  try {
    // Delete one by one as API is single delete
    for (const id of selectedIds.value) {
      await mcpToolsApi.deleteTool(id)
    }
    await fetchTools()
    selectedIds.value = []
  } catch (error) {
    console.error('Failed to delete selected tools:', error)
    alert('部分删除失败')
  }
}
</script>

<template>
  <div class="mcp-tools-mng">
    <section v-if="viewMode === 'list'" class="mcp-section">
      <div class="section-header">
        <h2 class="section-title">{{ t('mcp.toolListTitle') }}</h2>
        <div class="toolbar">
          <button type="button" class="btn-primary" @click="createTool">新建</button>
          <div class="search-box">
            <input
              v-model="keyword"
              type="text"
              class="search-input"
              placeholder="名称检索"
            />
          </div>
          <button type="button" class="btn-secondary" @click="toggleSelectAll">
            {{ isAllSelected ? '取消全选' : '全选' }}
          </button>
          <button type="button" class="btn-secondary danger" @click="removeSelected">
            删除
          </button>
        </div>
      </div>
      <div class="table-wrap">
        <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th class="col-select">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                />
              </th>
              <th class="col-name">名称</th>
              <th class="col-type">类型</th>
              <th class="col-time">注册时间</th>
              <th class="col-time">更新时间</th>
              <th class="col-desc">工具描述</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="filteredList.length === 0">
              <td colspan="7" class="empty-cell">{{ t('common.noData') }}</td>
            </tr>
            <tr v-for="item in filteredList" :key="item.id">
              <td class="col-select">
                <input
                  type="checkbox"
                  :checked="isSelected(item.id)"
                  @change="toggleRowSelection(item.id, $event.target.checked)"
                />
              </td>
              <td class="col-name">{{ item.name }}</td>
              <td class="col-type">{{ toolTypeLabel(item.type) }}</td>
              <td class="col-time">{{ item.registeredAt }}</td>
              <td class="col-time">{{ item.updatedAt }}</td>
              <td class="col-desc">{{ item.description }}</td>
              <td class="col-actions">
                <div class="action-group">
                  <button type="button" class="action-btn" @click="viewTool(item)">
                    查看
                  </button>
                  <button type="button" class="action-btn" @click="editTool(item)">
                    编辑
                  </button>
                  <button type="button" class="action-btn danger" @click="removeTool(item)">
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-else class="mcp-section">
      <div class="form-header">
        <button type="button" class="back-btn" @click="backToList">
          <span class="back-arrow">←</span>
          <span class="back-text">返回</span>
        </button>
        <!-- <h2 class="section-title">
          {{ formMode === 'create' ? '新建 MCP 工具' : '编辑 MCP 工具' }}
        </h2> -->
      </div>

      <div class="form-card">
        <div class="field-group">
          <div class="field-label">工具名称</div>
          <input
            v-model="formName"
            type="text"
            class="field-input"
            placeholder="请输入工具名称"
          />
        </div>

        <div class="field-group">
          <div class="field-label">类型选择</div>
          <div class="type-switch">
            <button
              type="button"
              class="type-btn"
              :class="{ active: formType === 'hardware' }"
              @click="formType = 'hardware'"
            >
              智能硬件
            </button>
            <button
              type="button"
              class="type-btn"
              :class="{ active: formType === 'service' }"
              @click="formType = 'service'"
            >
              服务
            </button>
          </div>
        </div>

        <div v-if="formType === 'service'" class="field-group">
          <div class="field-label">MCP 服务器</div>
          <div class="server-select-row">
            <select v-model="selectedServerId" class="field-input">
              <option :value="null" disabled>请选择 MCP 服务器</option>
              <option v-for="server in serverList" :key="server.id" :value="server.id">
                {{ server.name }} ({{ server.baseUrl }})
              </option>
            </select>
            <button type="button" class="btn-secondary" @click="showAddServer = !showAddServer">
              {{ showAddServer ? '取消' : '添加' }}
            </button>
          </div>
          
          <div v-if="showAddServer" class="add-server-box">
            <input 
              v-model="newServerName" 
              type="text" 
              class="field-input small" 
              placeholder="服务器名称"
            />
            <input 
              v-model="newServerUrl" 
              type="text" 
              class="field-input small" 
              placeholder="Base URL (e.g. http://localhost:8000)"
            />
            <input 
              v-model="newServerApiKey" 
              type="password" 
              class="field-input small" 
              placeholder="API Key (选填)"
            />
            <button type="button" class="btn-primary small" @click="addMcpServer">确定</button>
          </div>
        </div>

        <div v-if="formType === 'service'" class="field-group">
          <div class="field-label">Endpoint URL</div>
          <input
            v-model="endpointUrl"
            type="text"
            class="field-input"
            placeholder="请输入 Endpoint URL (例如 /tools/my-tool)"
          />
        </div>

        <div v-if="formType === 'service'" class="field-group">
          <div class="field-label">API Key (选填)</div>
          <input
            v-model="apiKey"
            type="password"
            class="field-input"
            placeholder="请输入 API Key"
          />
        </div>

        <div v-if="formType === 'hardware'" class="field-group">
          <div class="field-label">MCP 工具路径 / URI</div>
          <input
            v-model="formPath"
            type="text"
            class="field-input"
            placeholder="请输入 MCP 工具路径或者 URI"
          />
        </div>

        <div v-if="formType === 'hardware'" class="field-group">
          <div class="field-label">API Key (选填)</div>
          <input
            v-model="apiKey"
            type="password"
            class="field-input"
            placeholder="请输入 API Key"
          />
        </div>

        <div class="field-group">
          <div class="field-label">描述</div>
          <textarea
            v-model="formDesc"
            class="field-input field-textarea"
            placeholder="请输入工具描述"
            rows="3"
          ></textarea>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="viewToolDetail">
            查看详情
          </button>
          <button type="button" class="btn-primary" @click="confirmTool">确定</button>
        </div>
      </div>
      
      <!-- Tool List Section (shown when View Details is clicked) -->
      <div v-if="showDetailList" class="form-card" style="margin-top: 24px;">
        <h3 class="section-title" style="margin-bottom: 16px;">工具列表</h3>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-name">名称</th>
                <th class="col-type">类型</th>
                <th class="col-desc">描述</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="discoveredTools.length === 0">
                <td colspan="3" class="empty-cell">{{ t('common.noData') }}</td>
              </tr>
              <tr v-for="item in discoveredTools" :key="item.id">
                <td class="col-name">{{ item.name }}</td>
                <td class="col-type">{{ toolTypeLabel(item.type) }}</td>
                <td class="col-desc">{{ item.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Detail Modal -->
    <div v-if="showViewModal" class="modal-overlay" @click.self="closeViewModal">
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">工具详情</h3>
          <button class="close-btn" @click="closeViewModal">×</button>
        </div>
        <div class="modal-body" v-if="viewingItem">
          <div class="info-grid">
            <div class="info-item">
              <span class="label">名称</span>
              <span class="value">{{ viewingItem.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">类型</span>
              <span class="value">{{ toolTypeLabel(viewingItem.type) }}</span>
            </div>
            <div class="info-item">
              <span class="label">Endpoint</span>
              <span class="value">{{ viewingItem.endpoint_url || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">注册时间</span>
              <span class="value">{{ viewingItem.registeredAt }}</span>
            </div>
          </div>
          <div class="info-section">
            <div class="label">描述</div>
            <div class="value-block">{{ viewingItem.description || '暂无描述' }}</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="closeViewModal">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mcp-tools-mng {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.mcp-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85rem;
}

.back-arrow {
  font-size: 0.9rem;
}

.form-card {
  margin-top: 4px;
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.server-select-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.add-server-box {
  display: flex;
  gap: 8px;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-top: 4px;
}

.field-input.small {
  padding: 4px 8px;
  font-size: 0.85rem;
}

.btn-primary.small {
  padding: 4px 12px;
  font-size: 0.85rem;
  white-space: nowrap;
}

.field-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.type-switch {
  display: inline-flex;
  gap: 8px;
  padding: 4px;
  border-radius: 999px;
  background: var(--bg-secondary);
}

.type-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;

  &.active {
    background: var(--accent-gradient);
    color: var(--button-text);
  }
}

.field-input {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9rem;
  width: 100%;
}

.field-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.btn-primary {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: var(--accent-gradient, linear-gradient(135deg, #22c55e, #16a34a));
  color: var(--button-text, #fff);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-box {
  min-width: 180px;
}

.search-input {
  width: 100%;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.btn-secondary {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.danger {
    border-color: rgba(248, 113, 113, 0.6);
    color: #fecaca;
  }
}

.table-wrap {
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;

  th {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    font-weight: 500;
    padding: 10px 14px;
    text-align: left;
    white-space: nowrap;
  }

  td {
    padding: 12px 14px;
    border-top: 1px solid var(--border-primary);
    color: var(--text-primary);
  }

  tr:hover td {
    background: rgba(255, 255, 255, 0.02);
  }
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 24px !important;
}

.col-select {
  width: 40px;
  text-align: center;
}

.col-name {
  width: 20%;
  font-weight: 500;
}

.col-type {
  width: 100px;
}

.col-time {
  width: 150px;
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.col-desc {
  color: var(--text-secondary);
}

.col-actions {
  width: 120px;
}

.action-group {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;

  &:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
  }

  &.danger {
    border-color: rgba(248, 113, 113, 0.4);
    color: #fca5a5;

    &:hover {
      background: rgba(248, 113, 113, 0.1);
    }
  }
}

.loading {
  padding: 32px;
  text-align: center;
  color: var(--text-secondary);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  width: 500px;
  max-width: 90vw;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  color: var(--text-secondary);
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.value {
  font-size: 0.95rem;
  font-weight: 500;
}

.value-block {
  font-size: 0.9rem;
  background: var(--bg-secondary);
  padding: 10px;
  border-radius: 8px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
