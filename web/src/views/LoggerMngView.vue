<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// 时间范围过滤：近24小时 / 近一周 / 近一个月
const timeFilter = ref('24h') // '24h' | '7d' | '30d'
// 日志类型过滤：设备 / Agent，可多选组合
const activeTypes = ref(['device', 'agent'])

const logs = ref([])

onMounted(() => {
  // 模拟一些日志数据，后续可对接真实接口
  const now = new Date()
  function addHours(date, diff) {
    return new Date(date.getTime() + diff * 60 * 60 * 1000)
  }

  logs.value = [
    {
      id: 1,
      time: addHours(now, -2),
      type: 'device',
      unit: '摄像头01',
      content: '设备「摄像头01」上线，心跳正常。'
    },
    {
      id: 2,
      time: addHours(now, -6),
      type: 'agent',
      unit: '警务助手',
      content: '智能体「警务助手」完成一次对话编排调用。'
    },
    {
      id: 3,
      time: addHours(now, -26),
      type: 'device',
      unit: '温度传感器A',
      content: '设备「温度传感器A」温度波动超出阈值。'
    },
    {
      id: 4,
      time: addHours(now, -3 * 24),
      type: 'agent',
      unit: '警务助手',
      content: 'Agent 调用 RAG 知识库命中 FAQ 文档。'
    },
    {
      id: 5,
      time: addHours(now, -10 * 24),
      type: 'device',
      unit: '边缘网关01',
      content: '设备「边缘网关01」网络抖动，触发自动重连。'
    },
    {
      id: 6,
      time: addHours(now, -20 * 24),
      type: 'agent',
      unit: '警务助手',
      content: '智能体任务编排超时，自动重试成功。'
    }
  ]
})

const timeOptions = [
  { id: '24h', labelKey: 'log.filters.last24h' },
  { id: '7d', labelKey: 'log.filters.last7d' },
  { id: '30d', labelKey: 'log.filters.last30d' }
]

const typeOptions = [
  { id: 'device', labelKey: 'log.types.device' },
  { id: 'agent', labelKey: 'log.types.agent' }
]

function toggleType(type) {
  const current = activeTypes.value.slice()
  const idx = current.indexOf(type)
  if (idx === -1) {
    current.push(type)
  } else {
    current.splice(idx, 1)
  }
  activeTypes.value = current
}

const filteredLogs = computed(() => {
  const now = new Date()
  let fromTime = null
  if (timeFilter.value === '24h') {
    fromTime = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  } else if (timeFilter.value === '7d') {
    fromTime = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  } else if (timeFilter.value === '30d') {
    fromTime = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
  }

  return logs.value
    .slice()
    .sort((a, b) => b.time.getTime() - a.time.getTime())
    .filter((log) => {
      if (fromTime && log.time < fromTime) return false
      if (activeTypes.value.length > 0 && !activeTypes.value.includes(log.type)) return false
      return true
    })
})

function formatTime(date) {
  if (!(date instanceof Date)) return date
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
}
</script>

<template>
  <div class="logger-mng">
    <div class="logger-header">
      <div class="logger-filters">
        <div class="logger-filter-group">
          <span class="logger-filter-label">{{ t('log.filterByTime', '按时间') }}</span>
          <div class="logger-filter-chips">
            <button
              v-for="opt in timeOptions"
              :key="opt.id"
              type="button"
              class="filter-chip"
              :class="{ active: timeFilter === opt.id }"
              @click="timeFilter = opt.id"
            >
              {{ t(opt.labelKey) }}
            </button>
          </div>
        </div>
        <div class="logger-filter-group">
          <span class="logger-filter-label">{{ t('log.filterByType', '按类型') }}</span>
          <div class="logger-filter-chips">
            <button
              v-for="opt in typeOptions"
              :key="opt.id"
              type="button"
              class="filter-chip"
              :class="{ active: activeTypes.includes(opt.id) }"
              @click="toggleType(opt.id)"
            >
              {{ t(opt.labelKey) }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="logger-table-wrap">
      <table class="logger-table">
        <thead>
          <tr>
            <th>{{ t('log.columns.time', '时间') }}</th>
            <th>{{ t('log.columns.type', '日志类型') }}</th>
            <th>{{ t('log.columns.unit', '执行单元') }}</th>
            <th>{{ t('log.columns.content', '日志内容') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="filteredLogs.length === 0">
            <td colspan="4" class="empty-cell">{{ t('common.noData') }}</td>
          </tr>
          <tr v-for="log in filteredLogs" :key="log.id">
            <td class="col-time">{{ formatTime(log.time) }}</td>
            <td class="col-type">
              <span class="type-pill" :class="log.type">
                {{ log.type === 'device' ? t('log.types.device') : t('log.types.agent') }}
              </span>
            </td>
            <td class="col-unit">{{ log.unit || '-' }}</td>
            <td class="col-content">{{ log.content }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.logger-mng {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.logger-header {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.logger-title {
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0;
}

.logger-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  justify-content: flex-start;
}

.logger-filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logger-filter-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.logger-filter-chips {
  display: inline-flex;
  gap: 6px;
}

.filter-chip {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    background: rgba(56, 189, 248, 0.16);
    border-color: rgba(56, 189, 248, 0.6);
    color: #e0f2fe;
    font-weight: 500;
  }
}

.logger-table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.logger-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.logger-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.logger-table th,
.logger-table td {
  padding: 10px 14px;
  text-align: left;
}

.logger-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.logger-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.logger-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px 12px;
}

.col-time {
  width: 180px;
  white-space: nowrap;
}

.col-type {
  width: 120px;
}

.type-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
}

.type-pill.device {
  background: rgba(34, 197, 94, 0.16);
  color: #bbf7d0;
}

.type-pill.agent {
  background: rgba(59, 130, 246, 0.16);
  color: #bfdbfe;
}
</style>