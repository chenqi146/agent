<script setup>
import { ref, onMounted } from 'vue'
import { mcpToolsApi } from '@/api/mcpTools'

const loading = ref(false)
const toolList = ref([])
const showModal = ref(false)
const formData = ref({
  skill_id: '',
  tool_id: '',
  rating: 0
})

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

async function fetchToolRatings() {
  try {
    loading.value = true
    const res = await mcpToolsApi.getToolRatingList({
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    })
    if (res && res.data && res.data.data) {
      toolList.value = res.data.data.items || []
      pagination.value.total = res.data.data.total || 0
    }
  } catch (e) {
    console.error('Failed to fetch tool ratings:', e)
  } finally {
    loading.value = false
  }
}

function openRateModal(tool) {
  formData.value = {
    skill_id: '', // User might need to enter this or it could be inferred
    tool_id: tool.id,
    rating: 0
  }
  showModal.value = true
}

async function submitRating() {
  if (!formData.value.tool_id) {
    alert('缺少工具ID')
    return
  }
  try {
    loading.value = true
    // If skill_id is missing, maybe use tool_id as fallback if backend supports it?
    // For now, let's assume user must enter it or we auto-fill if possible.
    // The backend requires skill_id.
    if (!formData.value.skill_id) {
        // Simple hack: use tool_id as skill_id if not provided, assuming 1:1 mapping for simple cases
        formData.value.skill_id = formData.value.tool_id
    }
    
    await mcpToolsApi.addToolRating(formData.value)
    alert('评分添加成功')
    showModal.value = false
    fetchToolRatings() // Refresh list
  } catch (e) {
    alert('添加失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function handlePageChange(newPage) {
  pagination.value.page = newPage
  fetchToolRatings()
}

onMounted(() => {
  fetchToolRatings()
})
</script>

<template>
  <div class="mcp-rating-view">
    <!-- Tool List Table -->
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>工具名称</th>
            <th>工具接口</th>
            <th>平均评分</th>
            <th>调用次数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && toolList.length === 0">
            <td colspan="6" class="text-center">加载中...</td>
          </tr>
          <tr v-else-if="toolList.length === 0">
            <td colspan="6" class="text-center">暂无数据</td>
          </tr>
          <tr v-for="tool in toolList" :key="tool.id">
            <td>{{ tool.id }}</td>
            <td>
              <div class="tool-name">{{ tool.display_name || tool.name }}</div>
              <div class="tool-type">{{ tool.tool_type }}</div>
            </td>
            <td class="code-font">{{ tool.endpoint_url || '-' }}</td>
            <td>
              <div class="rating-display">
                <span class="star">★</span>
                <span>{{ tool.avg_rating ? Number(tool.avg_rating).toFixed(1) : '0.0' }}</span>
              </div>
            </td>
            <td>{{ tool.call_count }}</td>
            <td>
              <button class="btn-sm btn-primary" @click="openRateModal(tool)">评分</button>
            </td>
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
          :disabled="toolList.length < pagination.pageSize" 
          @click="handlePageChange(pagination.page + 1)"
        >下一页</button>
      </div>
    </div>

    <!-- Rate Modal -->
    <div v-if="showModal" class="modal-overlay">
      <div class="modal-content">
        <h3>添加评分</h3>
        <div class="form-group">
          <label>工具ID</label>
          <input v-model="formData.tool_id" type="text" class="text-input" disabled />
        </div>
        <div class="form-group">
          <label>技能ID (可选)</label>
          <input v-model="formData.skill_id" type="text" class="text-input" placeholder="如果不填则默认为工具ID" />
        </div>
        <div class="form-group">
          <label>评分 (0-5)</label>
          <div class="rating-input">
             <input v-model.number="formData.rating" type="range" min="0" max="5" step="0.5" />
             <span>{{ formData.rating }}</span>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showModal = false">取消</button>
          <button class="btn-primary" @click="submitRating" :disabled="loading">提交</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mcp-rating-view {
  padding: 20px;
  color: var(--text-primary);
}

.section-header {
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-primary);
  padding-bottom: 10px;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 600;
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

.tool-name {
  font-weight: 500;
}

.tool-type {
  font-size: 0.85em;
  color: var(--text-secondary);
}

.code-font {
  font-family: monospace;
  font-size: 0.9em;
  color: var(--accent-primary);
}

.rating-display {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #fbbf24; /* Amber */
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

.rating-input {
  display: flex;
  align-items: center;
  gap: 10px;
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

.btn-sm {
  padding: 4px 8px;
  font-size: 0.9em;
}
</style>
