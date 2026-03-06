<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'

const { t } = useI18n()

const ruleList = ref([])
const alertList = ref([])
const statsCategories = ref([])
const loading = ref(false)
const chartContainer = ref(null)
let chartInstance = null

const AUDIT_TYPES = {
  ai: 'log.audit.auditTypes.ai',
  keyword: 'log.audit.auditTypes.keyword',
  threshold: 'log.audit.auditTypes.threshold'
}

onMounted(() => {
  loading.value = true
  setTimeout(() => {
    statsCategories.value = [
      { id: 'device', labelKey: 'log.types.device', count: 128 },
      { id: 'agent', labelKey: 'log.types.agent', count: 256 },
      { id: 'api', labelKey: 'log.audit.statsApi', count: 89 },
      { id: 'error', labelKey: 'log.audit.statsError', count: 12 }
    ]
    ruleList.value = [
      {
        id: '1',
        name: '敏感词过滤',
        auditType: 'keyword',
        createdAt: '2025-01-10 09:00',
        content: '匹配关键字：违规、敏感',
        callCount: 342
      },
      {
        id: '2',
        name: 'AI 内容合规',
        auditType: 'ai',
        createdAt: '2025-01-12 14:20',
        content: 'AI 输出内容合规检测',
        callCount: 156
      },
      {
        id: '3',
        name: '错误率阈值',
        auditType: 'threshold',
        createdAt: '2025-01-15 11:00',
        content: '错误率 > 5% 触发告警',
        callCount: 28
      }
    ]
    alertList.value = [
      {
        id: '1',
        time: '2025-02-06 10:23:15',
        rule: '错误率阈值',
        level: 'critical',
        content: 'Agent 调用错误率 8.2% 超过阈值 5%'
      },
      {
        id: '2',
        time: '2025-02-06 09:15:00',
        rule: '敏感词过滤',
        level: 'warning',
        content: '检测到敏感词命中，已拦截'
      }
    ]
    loading.value = false
    nextTick(() => initStatsChart())
  }, 200)
})

function initStatsChart() {
  if (!chartContainer.value || !statsCategories.value.length) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartContainer.value)
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'var(--border-primary)',
      textStyle: { color: '#e2e8f0' }
    },
    grid: { left: '12%', right: '8%', top: '15%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: statsCategories.value.map((c) => t(c.labelKey)),
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.4)' } },
      axisLabel: { color: '#94a3b8', fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } },
      axisLabel: { color: '#94a3b8', fontSize: 12 }
    },
    series: [
      {
        type: 'bar',
        data: statsCategories.value.map((c, i) => {
          const colors = [
            'rgba(34, 197, 94, 0.85)',   // 设备 - 绿
            'rgba(59, 130, 246, 0.85)',  // Agent - 蓝
            'rgba(251, 191, 36, 0.85)',  // API - 黄
            'rgba(248, 113, 113, 0.85)'  // 异常 - 红
          ]
          return { value: c.count, itemStyle: { color: colors[i % colors.length] } }
        }),
        barWidth: '10%'
      }
    ]
  }
  chartInstance.setOption(option)
}

watch(statsCategories, () => {
  if (statsCategories.value.length && chartContainer.value) initStatsChart()
}, { deep: true })

function onResize() {
  chartInstance?.resize()
}

onMounted(() => {
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

function auditTypeLabel(type) {
  return t(AUDIT_TYPES[type] || type)
}

function levelLabel(level) {
  const key = 'log.audit.levels.' + level
  const out = t(key)
  return out !== key ? out : level
}

function viewAlert(item) {
  alert(t('log.audit.view') + ': ' + item.content)
}

function aiFixAlert(item) {
  alert(t('log.audit.aiFix') + ': ' + item.rule)
}

function pushAlert(item) {
  alert(t('log.audit.push') + ': ' + item.rule)
}
</script>

<template>
  <div class="logger-audit">
    <!-- 日志统计分类：直方图 -->
    <section class="audit-section">
      <h2 class="section-title">{{ t('log.audit.statsCategory') }}</h2>
      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div v-else ref="chartContainer" class="stats-chart"></div>
    </section>

    <!-- 规则管理 -->
    <section class="audit-section">
      <h2 class="section-title">{{ t('log.audit.ruleTitle') }}</h2>
      <div class="table-wrap">
        <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>{{ t('log.audit.ruleColumns.name') }}</th>
              <th>{{ t('log.audit.ruleColumns.auditType') }}</th>
              <th>{{ t('log.audit.ruleColumns.createdAt') }}</th>
              <th>{{ t('log.audit.ruleColumns.content') }}</th>
              <th>{{ t('log.audit.ruleColumns.callCount') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="ruleList.length === 0">
              <td colspan="5" class="empty-cell">{{ t('common.noData') }}</td>
            </tr>
            <tr v-for="item in ruleList" :key="item.id">
              <td class="col-name">{{ item.name }}</td>
              <td class="col-type">{{ auditTypeLabel(item.auditType) }}</td>
              <td class="col-time">{{ item.createdAt }}</td>
              <td class="col-content">{{ item.content }}</td>
              <td class="col-count">{{ item.callCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 审计告警 -->
    <section class="audit-section">
      <h2 class="section-title">{{ t('log.audit.alertTitle') }}</h2>
      <div class="table-wrap">
        <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>{{ t('log.audit.alertColumns.time') }}</th>
              <th>{{ t('log.audit.alertColumns.rule') }}</th>
              <th>{{ t('log.audit.alertColumns.level') }}</th>
              <th>{{ t('log.audit.alertColumns.content') }}</th>
              <th class="col-actions">{{ t('log.audit.alertColumns.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="alertList.length === 0">
              <td colspan="5" class="empty-cell">{{ t('common.noData') }}</td>
            </tr>
            <tr v-for="item in alertList" :key="item.id">
              <td class="col-time">{{ item.time }}</td>
              <td class="col-rule">{{ item.rule }}</td>
              <td class="col-level">
                <span class="level-pill" :class="item.level">{{ levelLabel(item.level) }}</span>
              </td>
              <td class="col-content">{{ item.content }}</td>
              <td class="col-actions">
                <div class="action-group">
                  <button type="button" class="action-btn" @click="viewAlert(item)">
                    {{ t('log.audit.view') }}
                  </button>
                  <button type="button" class="action-btn accent" @click="aiFixAlert(item)">
                    {{ t('log.audit.aiFix') }}
                  </button>
                  <button type="button" class="action-btn" @click="pushAlert(item)">
                    {{ t('log.audit.push') }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.logger-audit {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.audit-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.loading {
  padding: 24px;
  text-align: center;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.stats-chart {
  width: 100%;
  height: 260px;
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
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

.col-name {
  min-width: 100px;
}

.col-type {
  width: 90px;
}

.col-time {
  width: 160px;
  white-space: nowrap;
}

.col-content {
  max-width: 280px;
  color: var(--text-secondary);
}

.col-count {
  width: 90px;
}

.col-rule {
  min-width: 100px;
}

.col-level {
  width: 80px;
}

.level-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 0.78rem;
}

.level-pill.critical {
  background: rgba(248, 113, 113, 0.2);
  color: #fecaca;
}

.level-pill.warning {
  background: rgba(251, 191, 36, 0.2);
  color: #fde68a;
}

.level-pill.info {
  background: rgba(56, 189, 248, 0.2);
  color: #bae6fd;
}

.col-actions {
  width: 200px;
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
  flex-wrap: wrap;
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

  &.accent {
    border-color: rgba(34, 197, 94, 0.5);
    color: #86efac;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}
</style>
