<script setup>
import { ref, onMounted } from 'vue'
import { mcpToolsApi } from '@/api/mcpTools'

// State
const currentView = ref('list') // 'list' or 'create'
const loading = ref(false)
const versionList = ref([])
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const formData = ref({
  tool_id: '',
  version: '',
  interface_type: 'full',
  description: '',
  input_schema: '',
  output_schema: ''
})

// Methods
async function fetchVersions() {
  try {
    loading.value = true
    const res = await mcpToolsApi.getVersionList({
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    })
    
    if (res && res.data) {
      if (res.data.items) {
        versionList.value = res.data.items
        pagination.value.total = res.data.total
      } else if (res.data.snapshots) {
        // Fallback if backend returns snapshots (should not happen for global list)
        versionList.value = res.data.snapshots
        pagination.value.total = res.data.snapshots.length
      }
    }
  } catch (e) {
    console.error('Failed to fetch versions:', e)
  } finally {
    loading.value = false
  }
}

function switchToCreate() {
  formData.value = {
    tool_id: '',
    version: '',
    interface_type: 'full',
    description: '',
    input_schema: '',
    output_schema: ''
  }
  currentView.value = 'create'
}

function switchToList() {
  currentView.value = 'list'
  fetchVersions()
}

async function handleCreate() {
  if (!formData.value.tool_id || !formData.value.version) {
    alert('请填写工具ID和版本号')
    return
  }
  
  try {
    loading.value = true
    await mcpToolsApi.createVersion(formData.value)
    alert('版本创建成功')
    switchToList()
  } catch (e) {
    alert('创建失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function handlePageChange(newPage) {
  if (newPage < 1 || newPage > Math.ceil(pagination.value.total / pagination.value.pageSize)) return
  pagination.value.page = newPage
  fetchVersions()
}

onMounted(() => {
  fetchVersions()
})
</script>

<template>
  <div class="mcp-tool-version-view">
    
    <!-- List View -->
    <div v-if="currentView === 'list'" class="view-container">
      <div class="section-header">
        <!-- <h2 class="section-title">快照版本管理</h2> -->
        <button class="btn-primary" @click="switchToCreate">创建版本</button>
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>工具名称 (ID)</th>
              <th>版本号</th>
              <th>接口类型</th>
              <th>描述</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="text-center">加载中...</td>
            </tr>
            <tr v-else-if="versionList.length === 0">
              <td colspan="6" class="text-center">暂无数据</td>
            </tr>
            <tr v-else v-for="ver in versionList" :key="ver.id">
              <td>{{ ver.id }}</td>
              <td>
                <span v-if="ver.tool_name">{{ ver.tool_name }}</span>
                <span class="sub-text"> ({{ ver.tool_id }})</span>
              </td>
              <td>{{ ver.version }}</td>
              <td>
                <span :class="['status-badge', ver.interface_type === 'full' ? 'status-full' : 'status-compact']">
                  {{ ver.interface_type }}
                </span>
              </td>
              <td>{{ ver.description || '-' }}</td>
              <td>{{ ver.created_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="pagination" v-if="pagination.total > 0">
        <button 
          class="btn-icon" 
          :disabled="pagination.page === 1"
          @click="handlePageChange(pagination.page - 1)"
        >
          &lt;
        </button>
        <span class="page-info">
          {{ pagination.page }} / {{ Math.ceil(pagination.total / pagination.pageSize) }}
        </span>
        <button 
          class="btn-icon" 
          :disabled="pagination.page >= Math.ceil(pagination.total / pagination.pageSize)"
          @click="handlePageChange(pagination.page + 1)"
        >
          &gt;
        </button>
      </div>
    </div>

    <!-- Create View -->
    <div v-else-if="currentView === 'create'" class="view-container">
      <div class="section-header">
        <div class="header-left">
          <button class="btn-back" @click="switchToList">← 返回版本列表</button>
          <!-- <h2 class="section-title">创建新版本</h2> -->
        </div>
      </div>

      <div class="form-card">
        <div class="form-group">
          <label>工具ID <span class="required">*</span></label>
          <input v-model="formData.tool_id" type="number" class="text-input" placeholder="请输入关联的工具ID" />
        </div>

        <div class="form-group">
          <label>版本号 <span class="required">*</span></label>
          <input v-model="formData.version" type="text" class="text-input" placeholder="例如: v1.0.0" />
        </div>

        <div class="form-group">
          <label>接口类型</label>
          <select v-model="formData.interface_type" class="text-input">
            <option value="full">Full (完整)</option>
            <option value="compact">Compact (精简)</option>
          </select>
        </div>

        <div class="form-group">
          <label>描述</label>
          <textarea v-model="formData.description" class="text-input textarea" placeholder="版本描述说明"></textarea>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>输入Schema (JSON)</label>
            <textarea v-model="formData.input_schema" class="text-input code-area" placeholder="{}"></textarea>
          </div>
          <div class="form-group half">
            <label>输出Schema (JSON)</label>
            <textarea v-model="formData.output_schema" class="text-input code-area" placeholder="{}"></textarea>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn-secondary" @click="switchToList">取消</button>
          <button class="btn-primary" @click="handleCreate" :disabled="loading">
            {{ loading ? '提交中...' : '创建版本' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.mcp-tool-version-view {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  color: var(--text-primary);
}

.view-container {
  max-width: 1200px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.btn-primary {
  padding: 8px 20px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 20px;
  background: transparent;
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-secondary:hover {
  background: var(--bg-secondary);
}

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.95rem;
  padding: 4px 8px;
  border-radius: 4px;
}

.btn-back:hover {
  color: var(--text-primary);
  background: var(--bg-secondary);
}

.table-container {
  background: var(--bg-secondary);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.data-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.data-table th,
.data-table td {
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border-primary);
}

.data-table th {
  font-weight: 500;
  color: var(--text-muted);
}

.data-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.data-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.text-center {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
}

.sub-text {
  color: var(--text-secondary);
  font-size: 0.85rem;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-full {
  background: rgba(52, 211, 153, 0.2);
  color: #34d399;
}

.status-compact {
  background: rgba(96, 165, 250, 0.2);
  color: #60a5fa;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-top: 16px;
  gap: 12px;
}

.btn-icon {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  width: 32px;
  height: 32px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

/* Form Styles */
.form-card {
  background: var(--bg-secondary);
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  max-width: 800px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: flex;
  gap: 20px;
}

.half {
  flex: 1;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.required {
  color: #ef4444;
  margin-left: 4px;
}

.text-input {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.95rem;
  transition: border-color 0.2s;
}

.text-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.textarea {
  min-height: 80px;
  resize: vertical;
}

.code-area {
  font-family: monospace;
  min-height: 150px;
  font-size: 0.85rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--border-primary);
}
</style>
