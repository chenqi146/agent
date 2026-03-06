<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { memoryApi } from '@/api/memory'

const { t } = useI18n()

const activeTab = ref('content') // content | config

const timeFilter = ref('last1d') // last1d | last7d | last30d | last90d | all
const categoryFilter = ref('all') // all | preference | device | query | system
const categoryDropdownOpen = ref(false)
const roleTypeFilter = ref('all') // all | police | customerService | analyst
const roleTypeDropdownOpen = ref(false)
const searchKeyword = ref('')

const memories = ref([])
const selectedIds = ref([])
const detailItem = ref(null)

const saving = ref(false)
const saveSuccess = ref(false)
const saveError = ref('')

const memoryHalfLife = ref(24)
const autoForgetEnabled = ref(true)
const importanceWeight = ref(0.4)
const recencyWeight = ref(0.3)
const frequencyWeight = ref(0.3)
const compressThreshold = ref(200)
const summaryStyle = ref('compact_technical')
const contextMaxItems = ref(20)
const contextRetentionMinutes = ref(60)
const contextMaxCharsPerItem = ref(500)
const contextIncludeInLongTerm = ref(true)
const description = ref('')

async function loadMemories() {
  try {
    const resp = await memoryApi.searchContent({
      timeRange: timeFilter.value,
      category: categoryFilter.value,
      roleType: roleTypeFilter.value,
      keyword: searchKeyword.value.trim() || undefined,
      page: 1,
      pageSize: 100,
    })
    const data = resp?.data?.data || {}
    const items = data.items || []
    memories.value = items.map((m) => ({
      id: m.id,
      time: m.time,
      fact: m.fact,
      detail: m.detail,
      category: m.category,
      roleType: m.roleType,
    }))
    selectedIds.value = []
  } catch (err) {
    console.error('加载记忆内容失败', err)
  }
}

async function initMemoryPage() {
  try {
    await loadMemories()
  } catch (err) {
    console.error('初始化记忆内容失败', err)
  }
  try {
    const resp = await memoryApi.getConfig()
    const data = resp?.data?.data || {}
    if (data && Object.keys(data).length > 0) {
      memoryHalfLife.value = Number(data.memoryHalfLife ?? 24)
      autoForgetEnabled.value = Boolean(data.autoForgetEnabled ?? true)
      importanceWeight.value = Number(data.importanceWeight ?? 0.4)
      recencyWeight.value = Number(data.recencyWeight ?? 0.3)
      frequencyWeight.value = Number(data.frequencyWeight ?? 0.3)
      compressThreshold.value = Number(data.compressThreshold ?? 200)
      summaryStyle.value = data.summaryStyle || 'compact_technical'
      contextMaxItems.value = Number(data.contextMaxItems ?? 20)
      contextRetentionMinutes.value = Number(
        data.contextRetentionMinutes ?? 60
      )
      contextMaxCharsPerItem.value = Number(
        data.contextMaxCharsPerItem ?? 500
      )
      contextIncludeInLongTerm.value = Boolean(
        data.contextIncludeInLongTerm ?? true
      )
      description.value = data.description || ''
    }
  } catch (err) {
    console.error('加载记忆配置失败', err)
  }
}

onMounted(() => {
  initMemoryPage()
})

const timeOptions = [
  { id: 'last1d', labelKey: 'memory.timeFilters.last1d' },
  { id: 'last7d', labelKey: 'memory.timeFilters.last7d' },
  { id: 'last30d', labelKey: 'memory.timeFilters.last30d' },
  { id: 'last90d', labelKey: 'memory.timeFilters.last90d' },
  { id: 'all', labelKey: 'memory.timeFilters.all' },
]

const categoryOptions = [
  { id: 'all', labelKey: 'memory.categories.all' },
  { id: 'preference', labelKey: 'memory.categories.preference' },
  { id: 'device', labelKey: 'memory.categories.device' },
  { id: 'query', labelKey: 'memory.categories.query' },
  { id: 'system', labelKey: 'memory.categories.system' },
]

const roleTypeOptions = [
  { id: 'all', labelKey: 'memory.roleTypes.all' },
  { id: 'police', labelKey: 'memory.roleTypes.police' },
  { id: 'customerService', labelKey: 'memory.roleTypes.customerService' },
  { id: 'analyst', labelKey: 'memory.roleTypes.analyst' },
]

const allChecked = computed(
  () =>
    filteredMemories.value.length > 0 &&
    filteredMemories.value.every((m) => selectedIds.value.includes(m.id)),
)

const filteredMemories = computed(() => memories.value)

function formatTime(value) {
  if (value instanceof Date) {
    const y = value.getFullYear()
    const m = String(value.getMonth() + 1).padStart(2, '0')
    const d = String(value.getDate()).padStart(2, '0')
    const hh = String(value.getHours()).padStart(2, '0')
    const mm = String(value.getMinutes()).padStart(2, '0')
    const ss = String(value.getSeconds()).padStart(2, '0')
    return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
  }
  return value
}

function categoryLabel(category) {
  const opt = categoryOptions.find((o) => o.id === category)
  return opt ? t(opt.labelKey) : category
}

function roleTypeLabel(roleType) {
  const opt = roleTypeOptions.find((o) => o.id === roleType)
  return opt ? t(opt.labelKey) : roleType || '—'
}

async function removeMemory(item) {
  if (!window.confirm(t('memory.confirmDeleteSingle', '确定删除该条记忆吗？'))) return
  try {
    await memoryApi.deleteContent([item.id])
    memories.value = memories.value.filter((m) => m.id !== item.id)
    selectedIds.value = selectedIds.value.filter((id) => id !== item.id)
  } catch (err) {
    console.error('删除记忆失败', err)
  }
}

async function clearAll() {
  if (!memories.value.length) return
  if (!window.confirm(t('memory.confirmClearAll'))) return
  try {
    await memoryApi.clearContent()
    memories.value = []
    selectedIds.value = []
  } catch (err) {
    console.error('清空记忆失败', err)
  }
}

function toggleRow(id, checked) {
  const next = new Set(selectedIds.value)
  if (checked) {
    next.add(id)
  } else {
    next.delete(id)
  }
  selectedIds.value = Array.from(next)
}

function toggleAll(checked) {
  if (!checked) {
    selectedIds.value = []
    return
  }
  selectedIds.value = filteredMemories.value.map((m) => m.id)
}

async function bulkDelete() {
  if (!selectedIds.value.length) return
  if (!window.confirm(t('memory.confirmBulkDelete', '确定删除选中的记忆吗？'))) return
  const set = new Set(selectedIds.value)
  try {
    await memoryApi.deleteContent(Array.from(set))
    memories.value = memories.value.filter((m) => !set.has(m.id))
    selectedIds.value = []
  } catch (err) {
    console.error('批量删除记忆失败', err)
  }
}

function openDetail(item) {
  detailItem.value = item
}

function closeDetail() {
  detailItem.value = null
}

async function handleSaveConfig() {
  if (saving.value) return
  saveSuccess.value = false
  saveError.value = ''
  saving.value = true
  try {
    const payload = {
      memoryHalfLife: Number(memoryHalfLife.value),
      autoForgetEnabled: Boolean(autoForgetEnabled.value),
      importanceWeight: Number(importanceWeight.value),
      recencyWeight: Number(recencyWeight.value),
      frequencyWeight: Number(frequencyWeight.value),
      compressThreshold: Number(compressThreshold.value),
      summaryStyle: summaryStyle.value,
      contextMaxItems: Number(contextMaxItems.value),
      contextRetentionMinutes: Number(contextRetentionMinutes.value),
      contextMaxCharsPerItem: Number(contextMaxCharsPerItem.value),
      contextIncludeInLongTerm: Boolean(contextIncludeInLongTerm.value),
      description: description.value,
    }
    await memoryApi.saveConfig(payload)
    saveSuccess.value = true
  } catch (e) {
    console.error('保存记忆配置失败', e)
    const msg = e?.response?.data?.message || t('memory.saveFailed')
    saveError.value = msg
  } finally {
    saving.value = false
  }
}

watch(
  () => [timeFilter.value, categoryFilter.value, roleTypeFilter.value],
  () => {
    if (activeTab.value === 'content') {
      loadMemories()
    }
  },
)
</script>

<template>
  <div class="memory-mng">
    <div class="memory-subtabs">
      <button
        type="button"
        class="memory-subtab-btn"
        :class="{ active: activeTab === 'content' }"
        @click="activeTab = 'content'"
      >
        {{ t('memory.tabContent') }}
      </button>
      <button
        type="button"
        class="memory-subtab-btn"
        :class="{ active: activeTab === 'config' }"
        @click="activeTab = 'config'"
      >
        {{ t('memory.tabConfig') }}
      </button>
    </div>

    <div v-if="activeTab === 'content'" class="memory-content">
      <div class="memory-toolbar">
        <div class="memory-filters">
          <span class="filter-label">{{ t('memory.timeFilterLabel') }}</span>
          <div class="filter-chips">
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
          <div class="filter-divider" />
          <div class="category-select" @click="categoryDropdownOpen = !categoryDropdownOpen">
            <span class="category-select-label">
              {{ t('memory.categoryLabel', '记忆类型') }}
            </span>
            <span class="category-select-value">
              {{ categoryLabel(categoryFilter) }}
            </span>
            <span class="category-select-arrow" aria-hidden="true">
              ▾
            </span>
            <div
              v-if="categoryDropdownOpen"
              class="category-select-menu"
            >
              <button
                v-for="opt in categoryOptions"
                :key="opt.id"
                type="button"
                class="category-select-option"
                :class="{ active: categoryFilter === opt.id }"
                @click.stop="
                  categoryFilter = opt.id;
                  categoryDropdownOpen = false
                "
              >
                {{ t(opt.labelKey) }}
              </button>
            </div>
          </div>
          <div class="filter-divider" />
          <div class="category-select" @click="roleTypeDropdownOpen = !roleTypeDropdownOpen">
            <span class="category-select-label">
              {{ t('memory.roleTypeLabel', '角色类型') }}
            </span>
            <span class="category-select-value">
              {{ roleTypeLabel(roleTypeFilter) }}
            </span>
            <span class="category-select-arrow" aria-hidden="true">
              ▾
            </span>
            <div
              v-if="roleTypeDropdownOpen"
              class="category-select-menu"
            >
              <button
                v-for="opt in roleTypeOptions"
                :key="opt.id"
                type="button"
                class="category-select-option"
                :class="{ active: roleTypeFilter === opt.id }"
                @click.stop="
                  roleTypeFilter = opt.id;
                  roleTypeDropdownOpen = false
                "
              >
                {{ t(opt.labelKey) }}
              </button>
            </div>
          </div>
        </div>
        <div class="memory-actions">
          <input
            v-model="searchKeyword"
            type="text"
            class="search-input"
            :placeholder="t('memory.searchPlaceholder')"
          />
          <button
            type="button"
            class="btn-danger-outline"
            :disabled="!selectedIds.length"
            @click="bulkDelete"
          >
            {{ t('memory.bulkDelete', '批量删除') }}
          </button>
          <button
            type="button"
            class="btn-danger-outline"
            :disabled="!memories.length"
            @click="clearAll"
          >
            {{ t('memory.clearAll') }}
          </button>
        </div>
      </div>

      <div class="memory-table-wrap">
        <table class="memory-table">
          <thead>
            <tr>
              <th class="col-select">
                <input
                  type="checkbox"
                  :checked="allChecked"
                  @change="toggleAll($event.target.checked)"
                />
              </th>
              <th>{{ t('memory.columns.time') }}</th>
              <th>{{ t('memory.columns.fact') }}</th>
              <th>{{ t('memory.columns.roleType') }}</th>
              <th>{{ t('memory.columns.detail') }}</th>
              <th class="col-actions">{{ t('memory.columns.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="filteredMemories.length === 0">
              <td colspan="6" class="empty-cell">{{ t('common.noData') }}</td>
            </tr>
            <tr v-for="item in filteredMemories" :key="item.id">
              <td class="col-select">
                <input
                  type="checkbox"
                  :checked="selectedIds.includes(item.id)"
                  @change="toggleRow(item.id, $event.target.checked)"
                />
              </td>
              <td class="col-time">{{ formatTime(item.time) }}</td>
              <td class="col-fact">{{ categoryLabel(item.category) }}</td>
              <td class="col-role-type">{{ roleTypeLabel(item.roleType) }}</td>
              <td class="col-detail">{{ item.detail }}</td>
              <td class="col-actions">
                <div class="action-group">
                  <button type="button" class="action-btn" @click="openDetail(item)">
                    {{ t('memory.viewDetail') }}
                  </button>
                  <button type="button" class="action-btn danger" @click="removeMemory(item)">
                    {{ t('memory.delete') }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="memory-config">
      <div class="config-header">
        <h4 class="config-title">{{ t('memory.configTitle') }}</h4>
        <div class="config-header-actions">
          <button
            type="button"
            class="btn-primary"
            :disabled="saving"
            @click="handleSaveConfig"
          >
            {{ saving ? t('memory.saving') : t('memory.saveConfig') }}
          </button>
          <span v-if="saveSuccess" class="save-tip success">
            {{ t('memory.saveSuccess') }}
          </span>
          <span v-else-if="saveError" class="save-tip error">
            {{ saveError }}
          </span>
        </div>
      </div>

      <div class="config-section">
        <h5 class="config-section-title">{{ t('memory.sectionDecay') }}</h5>
        <div class="config-field">
          <label class="config-label">
            {{ t('memory.decayHalfLife') }}
          </label>
          <input
            v-model.number="memoryHalfLife"
            type="number"
            min="1"
            max="168"
            class="config-input"
          />
          <div class="config-hint">
            {{ t('memory.decayHint') }}
          </div>
        </div>
        <div class="config-field inline">
          <label class="config-label">
            <input v-model="autoForgetEnabled" type="checkbox" />
            <span>{{ t('memory.enableAutoForget') }}</span>
          </label>
        </div>
      </div>

      <div class="config-section">
        <h5 class="config-section-title">{{ t('memory.sectionScore') }}</h5>
        <div class="config-field">
          <label class="config-label">{{ t('memory.importanceWeight') }}</label>
          <input
            v-model.number="importanceWeight"
            type="number"
            min="0"
            max="1"
            step="0.01"
            class="config-input"
          />
        </div>
        <div class="config-field">
          <label class="config-label">{{ t('memory.recencyWeight') }}</label>
          <input
            v-model.number="recencyWeight"
            type="number"
            min="0"
            max="1"
            step="0.01"
            class="config-input"
          />
        </div>
        <div class="config-field">
          <label class="config-label">{{ t('memory.frequencyWeight') }}</label>
          <input
            v-model.number="frequencyWeight"
            type="number"
            min="0"
            max="1"
            step="0.01"
            class="config-input"
          />
        </div>
      </div>

      <div class="config-section">
        <h5 class="config-section-title">{{ t('memory.sectionCompress') }}</h5>
        <div class="config-field">
          <label class="config-label">
            {{ t('memory.compressThreshold') }}
          </label>
          <input
            v-model.number="compressThreshold"
            type="number"
            min="10"
            max="10000"
            class="config-input"
          />
          <div class="config-hint">
            {{ t('memory.compressThresholdHint') }}
          </div>
        </div>
        <div class="config-field">
          <label class="config-label">
            {{ t('memory.summaryStyle') }}
          </label>
          <select v-model="summaryStyle" class="config-input">
            <option value="compact_technical">
              {{ t('memory.summaryStyleDense') }}
            </option>
            <option value="narrative">
              {{ t('memory.summaryStyleNarrative') }}
            </option>
          </select>
        </div>
      </div>

      <div class="config-section">
        <h5 class="config-section-title">{{ t('memory.sectionContextShort') }}</h5>
        <div class="config-field">
          <label class="config-label">
            {{ t('memory.contextMaxItems') }}
          </label>
          <input
            v-model.number="contextMaxItems"
            type="number"
            min="5"
            max="200"
            class="config-input"
          />
          <div class="config-hint">
            {{ t('memory.contextMaxItemsHint') }}
          </div>
        </div>
        <div class="config-field">
          <label class="config-label">
            {{ t('memory.contextRetentionMinutes') }}
          </label>
          <input
            v-model.number="contextRetentionMinutes"
            type="number"
            min="5"
            max="1440"
            class="config-input"
          />
          <div class="config-hint">
            {{ t('memory.contextRetentionHint') }}
          </div>
        </div>
        <div class="config-field">
          <label class="config-label">
            {{ t('memory.contextMaxCharsPerItem') }}
          </label>
          <input
            v-model.number="contextMaxCharsPerItem"
            type="number"
            min="100"
            max="10000"
            class="config-input"
          />
          <div class="config-hint">
            {{ t('memory.contextMaxCharsHint') }}
          </div>
        </div>
        <div class="config-field inline">
          <label class="config-label">
            <input v-model="contextIncludeInLongTerm" type="checkbox" />
            <span>{{ t('memory.contextIncludeInLongTerm') }}</span>
          </label>
        </div>

        <div class="config-field">
          <label class="config-label">
            {{ t('memory.description') }}
          </label>
          <textarea
            v-model="description"
            rows="2"
            class="config-textarea"
          />
        </div>
      </div>


    </div>

    <div v-if="detailItem" class="memory-detail-overlay">
      <div class="memory-detail-dialog">
        <div class="detail-header">
          <h4 class="detail-title">{{ t('memory.viewDetail') }}</h4>
          <button type="button" class="detail-close" @click="closeDetail">
            ✕
          </button>
        </div>
        <div class="detail-body" v-if="detailItem">
          <div class="detail-row">
            <span class="detail-label">{{ t('memory.columns.time') }}</span>
            <span class="detail-value">{{ formatTime(detailItem.time) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ t('memory.columns.fact') }}</span>
            <span class="detail-value">{{ detailItem.fact }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ t('memory.columns.roleType') }}</span>
            <span class="detail-value">{{ roleTypeLabel(detailItem.roleType) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">{{ t('memory.columns.detail') }}</span>
            <span class="detail-value">{{ detailItem.detail }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.memory-mng {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.memory-subtabs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
}

.memory-subtab-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    color: var(--button-text);
    background: var(--accent-gradient);
  }
}

.memory-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.memory-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.memory-filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.filter-chips {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}

.filter-divider {
  width: 1px;
  height: 18px;
  background: rgba(148, 163, 184, 0.5);
  margin: 0 4px;
}

.category-select {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.6);
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(15, 23, 42, 0.7));
  cursor: pointer;
  font-size: 0.85rem;
  color: var(--text-secondary);
  transition: all 0.2s ease;

  &:hover {
    border-color: rgba(148, 163, 184, 0.9);
    color: var(--text-primary);
  }
}

.category-select-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.category-select-value {
  font-size: 0.85rem;
}

.category-select-arrow {
  font-size: 0.65rem;
  opacity: 0.85;
}

.category-select-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 160px;
  border-radius: 10px;
  border: 1px solid rgba(30, 64, 175, 0.8);
  background: radial-gradient(circle at top, rgba(37, 99, 235, 0.18), rgba(15, 23, 42, 0.98));
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.9);
  padding: 4px;
  z-index: 20;
}

.category-select-option {
  width: 100%;
  text-align: left;
  padding: 6px 8px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.82rem;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.45);
    color: #e5f2ff;
  }

  &.active {
    background: rgba(37, 99, 235, 0.85);
    color: #e5f2ff;
  }
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

.memory-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  min-width: 220px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.btn-danger-outline {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(248, 113, 113, 0.6);
  background: transparent;
  color: #fecaca;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:disabled {
    opacity: 0.5;
    cursor: default;
  }

  &:not(:disabled):hover {
    background: rgba(239, 68, 68, 0.15);
  }
}

.memory-table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.memory-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.memory-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.memory-table th,
.memory-table td {
  padding: 10px 14px;
  text-align: left;
}

.memory-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.memory-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.memory-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.col-select {
  width: 40px;
}

.col-time {
  width: 190px;
  white-space: nowrap;
}

.col-fact {
  width: 260px;
}

.col-role-type {
  width: 120px;
}

.col-detail {
  max-width: 520px;
}

.col-actions {
  width: 170px;
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
}

.action-btn {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.danger {
    border-color: rgba(248, 113, 113, 0.7);
    color: #fecaca;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.memory-config {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  padding: 16px 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.config-title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 4px;
}

.config-section {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.5);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-section-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 4px;

  &.inline {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }
}

.config-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.config-input {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
  max-width: 260px;

  /* Hide spin buttons for WebKit browsers */
  &::-webkit-outer-spin-button,
  &::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }
  /* Hide spin buttons for Firefox */
  -moz-appearance: textfield;
}

.config-range {
  max-width: 260px;
}

.config-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.config-header-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: var(--accent-gradient);
  color: var(--button-text);
  font-size: 0.85rem;
  cursor: pointer;
  transition: opacity 0.2s ease;

  &:disabled {
    opacity: 0.6;
    cursor: default;
  }
}

.save-tip {
  font-size: 0.8rem;

  &.success {
    color: #4ade80;
  }

  &.error {
    color: #fecaca;
  }
}

.config-textarea {
  min-height: 52px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
  resize: vertical;
}

.memory-detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
}

.memory-detail-dialog {
  width: 420px;
  max-width: 90vw;
  border-radius: 12px;
  background: #020617;
  border: 1px solid var(--border-primary);
  padding: 14px 16px 16px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.55);
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.detail-title {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 0;
}

.detail-close {
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.9rem;
}

.detail-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
}

.detail-row {
  display: flex;
  gap: 6px;
}

.detail-label {
  width: 54px;
  color: var(--text-muted);
}

.detail-value {
  flex: 1;
  color: var(--text-primary);
}
</style>
