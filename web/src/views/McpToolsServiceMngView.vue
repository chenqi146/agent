<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { mcpToolsApi } from '@/api/mcpTools'

const { t } = useI18n()

const logList = ref([])
const loading = ref(false)
const keyword = ref('')

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const LOG_TYPES = {
  smartDevice: 'mcp.toolTypes.smartDevice',
  virtualDevice: 'mcp.toolTypes.virtualDevice',
  function: 'mcp.toolTypes.function'
}

async function fetchToolLogs() {
  try {
    loading.value = true
    const res = await mcpToolsApi.getToolLogs({
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    })
    if (res && res.data && res.data.data) {
      logList.value = (res.data.data.items || []).map(item => ({
        id: item.id,
        name: item.tool_name || item.name || '-',
        type: item.tool_type || 'function',
        feature: item.tool_name || '-', // Placeholder
        time: item.called_at || item.created_at || '-',
        relation: '-' // Placeholder
      }))
      pagination.value.total = res.data.data.total || 0
    }
  } catch (e) {
    console.error('Failed to fetch tool logs:', e)
  } finally {
    loading.value = false
  }
}

function handlePageChange(newPage) {
  pagination.value.page = newPage
  fetchToolLogs()
}

onMounted(() => {
  fetchToolLogs()
})

const filteredList = computed(() => {
  const kw = keyword.value.trim()
  if (!kw) return logList.value
  return logList.value.filter((item) => item.name.includes(kw))
})

function typeLabel(type) {
  return t(LOG_TYPES[type] || type)
}
</script>

<template>
  <div class="mcp-log-mng">
    <div class="toolbar">
      <div class="search-box">
        <input
          v-model="keyword"
          type="text"
          class="search-input"
          placeholder="按名称检索"
        />
      </div>
    </div>

    <div class="table-wrap">
      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th class="col-name">名称</th>
            <th class="col-type">类型</th>
            <th class="col-func">功能</th>
            <th class="col-time">时间</th>
            <th class="col-relation">关联描述</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredList.length === 0">
            <td colspan="5" class="empty-cell">{{ t('common.noData') }}</td>
          </tr>
          <tr v-for="item in filteredList" :key="item.id">
            <td class="col-name">{{ item.name }}</td>
            <td class="col-type">{{ typeLabel(item.type) }}</td>
            <td class="col-func">{{ item.feature }}</td>
            <td class="col-time">{{ item.time }}</td>
            <td class="col-relation">{{ item.relation }}</td>
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
          :disabled="logList.length < pagination.pageSize" 
          @click="handlePageChange(pagination.page + 1)"
        >下一页</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mcp-log-mng {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-box {
  min-width: 200px;
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

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.loading {
  padding: 40px 24px;
  text-align: center;
  font-size: 0.9rem;
  color: var(--text-secondary);
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
}

.data-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.data-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.data-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.col-select {
  width: 5%;
  text-align: center;
}

.col-name {
  width: 18%;
}

.col-type {
  width: 10%;
}

.col-func {
  width: 18%;
  color: var(--text-secondary);
}

.col-time {
  width: 18%;
  white-space: nowrap;
}

.col-relation {
  width: 21%;
  color: var(--text-secondary);
}

.col-actions {
  width: 10%;
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px 12px;
}

.action-btn {
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.danger {
    border-color: rgba(248, 113, 113, 0.6);
    color: #fecaca;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}
</style>
