<script setup>
import { ref, onMounted } from 'vue'
import { mcpToolsApi } from '@/api/mcpTools'

const loading = ref(false)
const relationList = ref([])
const showModal = ref(false)
const formData = ref({
  source_tool_id: '',
  target_tool_id: '',
  relationship_type: '',
  weight: 1.0
})

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

async function fetchRelations() {
  try {
    loading.value = true
    const res = await mcpToolsApi.getToolRelations({
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    })
    if (res && res.data) {
      // The backend returns { items: [...], total: ... } for "all" list
      // Or { relationships: [...] } for specific tool list
      // My controller logic returns { items: ..., total: ... } if toolId is missing.
      if (res.data.items) {
        relationList.value = res.data.items
        pagination.value.total = res.data.total
      } else if (res.data.relationships) {
        relationList.value = res.data.relationships
        pagination.value.total = res.data.relationships.length
      }
    }
  } catch (e) {
    console.error('Failed to fetch relations:', e)
  } finally {
    loading.value = false
  }
}

function openAddModal() {
  formData.value = {
    source_tool_id: '',
    target_tool_id: '',
    relationship_type: '',
    weight: 1.0
  }
  showModal.value = true
}

async function submitRelation() {
  if (!formData.value.source_tool_id || !formData.value.target_tool_id || !formData.value.relationship_type) {
    alert('请填写完整信息')
    return
  }
  try {
    loading.value = true
    await mcpToolsApi.addToolRelation(formData.value)
    alert('添加成功')
    showModal.value = false
    fetchRelations()
  } catch (e) {
    alert('添加失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function handlePageChange(newPage) {
  pagination.value.page = newPage
  fetchRelations()
}

onMounted(() => {
  fetchRelations()
})
</script>

<template>
  <div class="mcp-relation-view">
    <div class="section-header">
      <!-- <h2 class="section-title">工具关系管理</h2> -->
      <button class="btn-primary" @click="openAddModal">添加关系</button>
    </div>

    <!-- Relation List Table -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>源工具</th>
            <th>目标工具</th>
            <th>关系类型</th>
            <th>权重</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && relationList.length === 0">
            <td colspan="5" class="text-center">加载中...</td>
          </tr>
          <tr v-else-if="relationList.length === 0">
            <td colspan="5" class="text-center">暂无数据</td>
          </tr>
          <tr v-for="item in relationList" :key="item.id">
            <td>{{ item.id }}</td>
            <td>
              <div class="tool-info">
                <span class="tool-name">{{ item.source_tool_name || '-' }}</span>
                <span class="tool-id">(ID: {{ item.source_tool_id }})</span>
              </div>
            </td>
            <td>
              <div class="tool-info">
                <span class="tool-name">{{ item.target_tool_name || '-' }}</span>
                <span class="tool-id">(ID: {{ item.target_tool_id }})</span>
              </div>
            </td>
            <td>
              <span class="badge">{{ item.relationship_type }}</span>
            </td>
            <td>{{ item.weight }}</td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <div class="pagination" v-if="pagination.total > 0">
        <button 
          :disabled="pagination.page === 1" 
          @click="handlePageChange(pagination.page - 1)"
        >上一页</button>
        <span>{{ pagination.page }}</span>
        <button 
          :disabled="relationList.length < pagination.pageSize" 
          @click="handlePageChange(pagination.page + 1)"
        >下一页</button>
      </div>
    </div>

    <!-- Add Modal -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <h3>添加工具关系</h3>
        <div class="form-group">
          <label>源工具ID</label>
          <input v-model="formData.source_tool_id" type="number" class="text-input" placeholder="输入源工具ID" />
        </div>
        <div class="form-group">
          <label>目标工具ID</label>
          <input v-model="formData.target_tool_id" type="number" class="text-input" placeholder="输入目标工具ID" />
        </div>
        <div class="form-group">
          <label>关系类型</label>
          <input v-model="formData.relationship_type" type="text" class="text-input" placeholder="例如: dependency, conflict" />
        </div>
        <div class="form-group">
          <label>权重 (0.0 - 1.0)</label>
          <input v-model.number="formData.weight" type="number" step="0.1" min="0" max="1" class="text-input" />
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showModal = false">取消</button>
          <button class="btn-primary" @click="submitRelation" :disabled="loading">提交</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mcp-relation-view {
  padding: 20px;
  color: var(--text-primary);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-primary);
  padding-bottom: 10px;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0;
}

.table-container {
  overflow-x: auto;
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

.tool-info {
  display: flex;
  flex-direction: column;
}

.tool-name {
  font-weight: 500;
}

.tool-id {
  font-size: 0.8em;
  color: var(--text-secondary);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  font-size: 0.85em;
}

.text-center {
  text-align: center;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  align-items: center;
  margin-top: 16px;
}

.pagination button {
  padding: 5px 10px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  cursor: pointer;
  border-radius: 4px;
}

.pagination button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-primary);
  padding: 20px;
  border-radius: 8px;
  width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.text-input {
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.btn-primary {
  padding: 8px 16px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  border-radius: 4px;
  cursor: pointer;
}
</style>
