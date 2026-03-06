<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'

const props = defineProps({
  /** true=弹层内使用，隐藏标题（弹层自带标题） */
  hideTitle: { type: Boolean, default: false },
  /** true=嵌入运行详情侧栏，隐藏整块标题+筛选行 */
  embedded: { type: Boolean, default: false }
})

const { t } = useI18n()

// 告警统计走势图
const statsTimeRange = ref('1h') // 10m | 1h | 1d | 1month
const statsChartContainer = ref(null)
let statsChartInstance = null

const statsTimeOptions = [
  { id: '10m', labelKey: 'alert.timeRange10m' },
  { id: '1h', labelKey: 'alert.timeRange1h' },
  { id: '1d', labelKey: 'alert.timeRange1d' },
  { id: '1month', labelKey: 'alert.timeRange1month' }
]

function getStatsChartData() {
  const now = Date.now()
  let points = 10
  let stepMs = 6 * 60 * 1000 // 1h: 6min per point
  if (statsTimeRange.value === '10m') {
    points = 10
    stepMs = 60 * 1000
  } else if (statsTimeRange.value === '1h') {
    points = 12
    stepMs = 5 * 60 * 1000
  } else if (statsTimeRange.value === '1d') {
    points = 24
    stepMs = 60 * 60 * 1000
  } else {
    points = 30
    stepMs = 24 * 60 * 60 * 1000
  }
  const xAxisData = []
  const fatalData = []
  const criticalData = []
  const normalData = []
  const infoData = []
  for (let i = points - 1; i >= 0; i--) {
    const t0 = new Date(now - i * stepMs)
    xAxisData.push(
      statsTimeRange.value === '1month'
        ? t0.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
        : t0.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    )
    fatalData.push(Math.floor(Math.random() * 5) + (i < 2 ? 1 : 0))
    criticalData.push(Math.floor(Math.random() * 8) + 1)
    normalData.push(Math.floor(Math.random() * 12) + 2)
    infoData.push(Math.floor(Math.random() * 15) + 3)
  }
  return { xAxisData, fatalData, criticalData, normalData, infoData }
}

function initStatsChart() {
  if (!statsChartContainer.value || props.embedded) return
  if (statsChartInstance) statsChartInstance.dispose()
  statsChartInstance = echarts.init(statsChartContainer.value)
  const { xAxisData, fatalData, criticalData, normalData, infoData } = getStatsChartData()
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'var(--border-primary)',
      textStyle: { color: '#e2e8f0' }
    },
    legend: {
      data: [
        t('alert.fatal'),
        t('alert.critical'),
        t('alert.normal'),
        t('alert.info')
      ],
      bottom: 0,
      textStyle: { color: '#94a3b8', fontSize: 11 }
    },
    grid: { left: '10%', right: '6%', top: '12%', bottom: '20%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.4)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } },
      axisLabel: { color: '#94a3b8', fontSize: 11 }
    },
    series: [
      { name: t('alert.fatal'), type: 'line', smooth: true, data: fatalData, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 }, itemStyle: { color: '#f87171' } },
      { name: t('alert.critical'), type: 'line', smooth: true, data: criticalData, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 }, itemStyle: { color: '#fb923c' } },
      { name: t('alert.normal'), type: 'line', smooth: true, data: normalData, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 }, itemStyle: { color: '#facc15' } },
      { name: t('alert.info'), type: 'line', smooth: true, data: infoData, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2 }, itemStyle: { color: '#38bdf8' } }
    ]
  }
  statsChartInstance.setOption(option)
}

watch(statsTimeRange, () => {
  if (statsChartInstance && statsChartContainer.value && !props.embedded) {
    const { xAxisData, fatalData, criticalData, normalData, infoData } = getStatsChartData()
    statsChartInstance.setOption({
      xAxis: { data: xAxisData },
      series: [
        { data: fatalData },
        { data: criticalData },
        { data: normalData },
        { data: infoData }
      ]
    })
  }
})

function onStatsResize() {
  statsChartInstance?.resize()
}

// 模拟传感器告警数据
const alerts = ref([
  {
    id: 1,
    name: '温度传感器异常',
    level: 'fatal',
    time: '2024-01-22 14:30:25',
    description: '温度传感器读数超出正常范围，当前温度95°C，可能导致设备损坏'
  },
  {
    id: 2,
    name: '湿度传感器异常',
    level: 'normal',
    time: '2024-01-22 14:28:10',
    description: '湿度传感器读数偏低，当前湿度35%'
  },
  {
    id: 3,
    name: '压力传感器异常',
    level: 'critical',
    time: '2024-01-22 14:25:30',
    description: '压力传感器读数过高，当前压力2.5MPa'
  },
  {
    id: 4,
    name: '气体传感器异常',
    level: 'info',
    time: '2024-01-22 14:20:15',
    description: '气体传感器检测到轻微泄漏'
  },
  {
    id: 5,
    name: '光敏传感器异常',
    level: 'critical',
    time: '2024-01-22 14:15:00',
    description: '光敏传感器读数异常，光照强度过低'
  },
  {
    id: 6,
    name: '烟雾传感器异常',
    level: 'fatal',
    time: '2024-01-22 14:10:30',
    description: '烟雾传感器检测到烟雾浓度超标，存在火灾风险'
  },
  {
    id: 7,
    name: '振动传感器异常',
    level: 'normal',
    time: '2024-01-22 14:05:20',
    description: '振动传感器检测到异常振动'
  },
  {
    id: 8,
    name: '位移传感器异常',
    level: 'info',
    time: '2024-01-22 14:00:15',
    description: '位移传感器读数超出预设范围'
  },
  {
    id: 9,
    name: '流量传感器异常',
    level: 'critical',
    time: '2024-01-22 13:55:10',
    description: '流量传感器检测到流量异常波动'
  },
  {
    id: 10,
    name: '液位传感器异常',
    level: 'normal',
    time: '2024-01-22 13:50:05',
    description: '液位传感器读数过低'
  },
  {
    id: 11,
    name: 'pH传感器异常',
    level: 'critical',
    time: '2024-01-22 13:45:00',
    description: 'pH传感器读数超出正常范围，当前pH值9.5'
  },
  {
    id: 12,
    name: '电导率传感器异常',
    level: 'info',
    time: '2024-01-22 13:40:30',
    description: '电导率传感器读数异常'
  },
  {
    id: 13,
    name: '红外传感器异常',
    level: 'normal',
    time: '2024-01-22 13:35:20',
    description: '红外传感器检测到异常热源'
  },
  {
    id: 14,
    name: '超声波传感器异常',
    level: 'critical',
    time: '2024-01-22 13:30:15',
    description: '超声波传感器读数不稳定'
  },
  {
    id: 15,
    name: '加速度传感器异常',
    level: 'warning',
    time: '2024-01-22 13:25:10',
    description: '加速度传感器检测到异常加速度'
  }
])

const selectedLevel = ref('all')
const currentPage = ref(1)
const pageSize = 12

// 获取告警等级文本
function getAlertLevelText(level) {
  const levelMap = {
    fatal: t('alert.fatal', '致命告警'),
    critical: t('alert.critical', '严重告警'),
    normal: t('alert.normal', '一般告警'),
    info: t('alert.info', '提示告警')
  }
  return levelMap[level] || level
}

const filteredAlerts = computed(() => {
  let result = alerts.value
  if (selectedLevel.value !== 'all') {
    result = result.filter(alert => alert.level === selectedLevel.value)
  }
  return result
})

const totalPages = computed(() => {
  return Math.ceil(filteredAlerts.value.length / pageSize)
})

const paginatedAlerts = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredAlerts.value.slice(start, end)
})

function handlePageChange(page) {
  currentPage.value = page
}

function handleIgnore(alert) {
  console.log('忽略告警:', alert)
  // TODO: 实现忽略告警的逻辑
}

function handleView(alert) {
  console.log('查看告警:', alert)
  // TODO: 实现查看告警的逻辑
}

function handleAIFix(alert) {
  console.log('AI修复:', alert)
  // TODO: 实现AI修复的逻辑
}

onMounted(() => {
  if (!props.embedded) {
    nextTick(() => initStatsChart())
    window.addEventListener('resize', onStatsResize)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onStatsResize)
  if (statsChartInstance) {
    statsChartInstance.dispose()
    statsChartInstance = null
  }
})
</script>

<template>
  <div class="warning-page">
    <div v-if="!embedded && !hideTitle" class="warning-header">
      <h1 class="page-title">{{ t('alert.title', '告警管理') }}</h1>
      <div class="filter-section">
        <select v-model="selectedLevel" class="level-filter">
          <option value="all">{{ t('alert.all', '全部') }}</option>
          <option value="fatal">{{ t('alert.fatal', '致命告警') }}</option>
          <option value="critical">{{ t('alert.critical', '严重告警') }}</option>
          <option value="normal">{{ t('alert.normal', '一般告警') }}</option>
          <option value="info">{{ t('alert.info', '提示告警') }}</option>
        </select>
      </div>
    </div>

    <!-- 告警统计走势图 -->
    <section v-if="!embedded" class="alert-stats-section">
      <h2 class="alert-stats-title">{{ t('alert.statsTitle', '告警统计') }}</h2>
      <div class="alert-stats-toolbar">
        <div class="alert-stats-time-chips">
          <button
            v-for="opt in statsTimeOptions"
            :key="opt.id"
            type="button"
            class="stats-time-chip"
            :class="{ active: statsTimeRange === opt.id }"
            @click="statsTimeRange = opt.id"
          >
            {{ t(opt.labelKey) }}
          </button>
        </div>
        <select v-if="hideTitle" v-model="selectedLevel" class="level-filter level-filter-inline">
          <option value="all">{{ t('alert.all', '全部') }}</option>
          <option value="fatal">{{ t('alert.fatal', '致命告警') }}</option>
          <option value="critical">{{ t('alert.critical', '严重告警') }}</option>
          <option value="normal">{{ t('alert.normal', '一般告警') }}</option>
          <option value="info">{{ t('alert.info', '提示告警') }}</option>
        </select>
      </div>
      <div ref="statsChartContainer" class="alert-stats-chart"></div>
    </section>

    <div class="warning-content">
      <div class="alert-list">
        <div 
          v-for="alert in paginatedAlerts" 
          :key="alert.id" 
          class="alert-item"
        >
          <div class="alert-header">
            <span class="alert-name">{{ alert.name }}</span>
            <span class="alert-level" :class="alert.level">{{
              getAlertLevelText(alert.level)
            }}</span>
          </div>
          <div class="alert-description">{{ alert.description }}</div>
          <div class="alert-time">{{ alert.time }}</div>
          <div class="alert-actions">
            <button class="alert-btn ignore" @click="handleIgnore(alert)">
              {{ t('alert.ignore', '忽略') }}
            </button>
            <button class="alert-btn view" @click="handleView(alert)">
              {{ t('alert.view', '查看') }}
            </button>
            <button class="alert-btn ai-fix" @click="handleAIFix(alert)">
              {{ t('alert.aiFix', 'AI修复') }}
            </button>
          </div>
        </div>
      </div>

      <div class="pagination" v-if="totalPages > 1">
        <button 
          class="page-btn" 
          :disabled="currentPage === 1"
          @click="handlePageChange(currentPage - 1)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <button 
          v-for="page in totalPages" 
          :key="page"
          class="page-btn"
          :class="{ active: currentPage === page }"
          @click="handlePageChange(page)"
        >
          {{ page }}
        </button>
        <button 
          class="page-btn" 
          :disabled="currentPage === totalPages"
          @click="handlePageChange(currentPage + 1)"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.warning-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.warning-header {
  padding: 24px 60px 24px 24px;
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;

  .page-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  &.header-compact {
    padding: 12px 24px 14px 24px;
    margin-bottom: 0;

    .filter-section {
      margin-left: auto;
    }
  }

  .filter-section {
    display: flex;
    gap: 12px;

    .level-filter {
      padding: 8px 12px;
      border: 1px solid var(--border-primary);
      border-radius: 6px;
      background: var(--bg-secondary);
      color: var(--text-primary);
      font-size: 0.875rem;
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover {
        border-color: var(--accent-primary);
      }

      &:focus {
        outline: none;
        border-color: var(--accent-primary);
      }
    }
  }
}

.alert-stats-section {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-stats-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.alert-stats-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.alert-stats-time-chips {
  display: inline-flex;
  gap: 8px;
  flex-wrap: wrap;
}

.level-filter-inline {
  padding: 6px 12px;
  border: 1px solid var(--border-primary);
  border-radius: 999px;
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.82rem;
  cursor: pointer;
}

.stats-time-chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.82rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    background: rgba(56, 189, 248, 0.16);
    border-color: rgba(56, 189, 248, 0.6);
    color: #e0f2fe;
    font-weight: 500;
  }

  &:hover:not(.active) {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.alert-stats-chart {
  width: 100%;
  height: 240px;
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.warning-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;

  // 自定义滚动条样式
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--border-primary);
    border-radius: 3px;

    &:hover {
      background: var(--text-muted);
    }
  }
}

.alert-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.alert-item {
  padding: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--accent-primary);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .alert-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;

    .alert-name {
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--text-primary);
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .alert-level {
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 0.65rem;
      font-weight: 500;
      flex-shrink: 0;

      &.fatal {
        background: rgba(220, 38, 38, 0.15);
        color: #dc2626;
      }

      &.critical {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }

      &.normal {
        background: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
      }

      &.info {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;
      }
    }
  }

  .alert-description {
    font-size: 0.75rem;
    color: var(--text-secondary);
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .alert-time {
    font-size: 0.65rem;
    color: var(--text-muted);
  }

  .alert-actions {
    display: flex;
    gap: 6px;
    padding-top: 6px;
    border-top: 1px solid var(--border-primary);

    .alert-btn {
      flex: 1;
      padding: 5px 10px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      border: none;
      text-align: center;

      &.ignore {
        background: var(--bg-tertiary);
        color: var(--text-secondary);

        &:hover {
          background: var(--bg-hover);
          color: var(--text-primary);
        }
      }

      &.view {
        background: var(--bg-secondary);
        border: 1px solid var(--border-primary);
        color: var(--text-primary);

        &:hover {
          border-color: var(--accent-primary);
          color: var(--accent-primary);
        }
      }

      &.ai-fix {
        background: var(--accent-primary);
        color: white;

        &:hover {
          opacity: 0.9;
        }
      }
    }
  }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--border-primary);

  .page-btn {
    min-width: 36px;
    height: 36px;
    padding: 0 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    border-radius: 4px;
    color: var(--text-primary);
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;

    svg {
      width: 18px;
      height: 18px;
    }

    &:hover:not(:disabled) {
      border-color: var(--accent-primary);
      color: var(--accent-primary);
      background: rgba(var(--accent-primary), 0.05);
    }

    &:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    &.active {
      background: var(--accent-primary);
      border-color: var(--accent-primary);
      color: white;
      font-weight: 600;
    }
  }
}
</style>