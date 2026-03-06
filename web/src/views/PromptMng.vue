<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import PromptOperaView from './PromptOperaView.vue'
import PromptTestView from './PromptTestView.vue'
import { promptApi } from '@/api/prompt'
import { message } from 'ant-design-vue'

const { t } = useI18n()

const activeTab = ref('list') // list | test
const listSubtab = ref('list') // list | opera
const operaMode = ref('create') // create | view | edit
const operaData = ref(null)

const list = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const size = ref(10)

async function loadList() {
  loading.value = true
  try {
    const res = await promptApi.list({
      page: page.value,
      size: size.value
    })
    if (res.data && res.data.code === 0 && res.data.data) {
      list.value = res.data.data.items || []
      total.value = res.data.data.total || 0
    } else {
      list.value = []
      total.value = 0
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadList()
})

function goCreate() {
  operaMode.value = 'create'
  operaData.value = null
  listSubtab.value = 'opera'
}

function goView(item) {
  operaMode.value = 'view'
  operaData.value = item
  listSubtab.value = 'opera'
}

function goEdit(item) {
  operaMode.value = 'edit'
  operaData.value = item
  listSubtab.value = 'opera'
}

function statusLabel(status) {
  if (status === 'draft') return t('prompt.statusDraft')
  return t('prompt.statusEnabled')
}

function getCategoryLabel(category) {
  if (!category) return '—'
  const key = `prompt.categories.${category}`
  const label = t(key)
  return label === key ? category : label
}

async function toggleStatus(item) {
  try {
    const newStatus = item.status === 'draft' ? 'enabled' : 'draft'
    await promptApi.toggleStatus(item.id, newStatus)
    item.status = newStatus
  } catch (e) {
    console.error(e)
  }
}

function backToList() {
  listSubtab.value = 'list'
  operaData.value = null
  loadList()
}

async function onOperaSave(data) {
  try {
    if (operaMode.value === 'create') {
      await promptApi.create(data)
    } else if (operaMode.value === 'edit') {
      await promptApi.update({
        id: operaData.value.id,
        ...data
      })
    }
    listSubtab.value = 'list'
    operaData.value = null
    loadList()
  } catch (e) {
    console.error(e)
    alert('Save failed: ' + e.message)
  }
}

async function remove(item) {
  if (!window.confirm(t('prompt.confirmDelete', { name: item.name }))) return
  try {
    await promptApi.delete(item.id)
    loadList()
  } catch (e) {
    console.error(e)
  }
}

function normalizeFileName(name) {
  const base = String(name || '').trim() || 'prompt'
  return base
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .slice(0, 120)
}

async function doExport(item) {
  try {
    let promptContent = item?.content
    if (!promptContent && item?.id) {
      const res = await promptApi.getDetail(item.id)
      if (res.data && res.data.code === 0 && res.data.data) {
        promptContent = res.data.data.content
      }
    }
    if (!promptContent) {
      message.error(t('common.noData'))
      return
    }

    const filename = `${normalizeFileName(item?.name)}.txt`
    const blob = new Blob([promptContent], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    message.success(t('prompt.export') + ': ' + filename)
  } catch (e) {
    console.error(e)
    message.error(t('common.error'))
  }
}

function onEditTemplateFromTest(item) {
  activeTab.value = 'list'
  listSubtab.value = 'opera'
  operaMode.value = 'edit'
  operaData.value = item
}
</script>

<template>
  <div class="prompt-mng">
    <div class="prompt-subtabs">
      <button
        type="button"
        class="prompt-subtab-btn"
        :class="{ active: activeTab === 'list' }"
        @click="activeTab = 'list'"
      >
        {{ t('prompt.tabList') }}
      </button>
      <button
        type="button"
        class="prompt-subtab-btn"
        :class="{ active: activeTab === 'test' }"
        @click="activeTab = 'test'"
      >
        {{ t('prompt.tabTest') }}
      </button>
    </div>

    <!-- 提示词列表 -->
    <template v-if="activeTab === 'list'">
      <template v-if="listSubtab === 'list'">
        <div class="prompt-list-header">
          <button type="button" class="btn-create" @click="goCreate">
            {{ t('prompt.create') }}
          </button>
        </div>
        <div class="prompt-table-wrap">
          <div v-if="loading" class="prompt-loading">{{ t('common.loading') }}</div>
          <table v-else class="prompt-table">
            <thead>
              <tr>
                <th class="col-name">{{ t('prompt.columns.name') }}</th>
                <th class="col-version">{{ t('prompt.version') }}</th>
                <th class="col-category">{{ t('prompt.columns.category') }}</th>
                <th class="col-time">{{ t('prompt.columns.createdAt') }}</th>
                <th class="col-time">{{ t('prompt.columns.updatedAt') }}</th>
                <th class="col-status">{{ t('prompt.columns.status') }}</th>
                <th class="col-actions">{{ t('prompt.columns.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="list.length === 0">
                <td colspan="7" class="empty-cell">{{ t('common.noData') }}</td>
              </tr>
              <tr v-for="item in list" :key="item.id">
                <td class="col-name">{{ item.name }}</td>
                <td class="col-version">{{ item.version || '1.0.0' }}</td>
                <td class="col-category">{{ getCategoryLabel(item.category) }}</td>
                <td class="col-time">{{ item.createdAt }}</td>
                <td class="col-time">{{ item.updatedAt }}</td>
                <td class="col-status">
                  <span class="status-tag" :class="item.status">
                    {{ statusLabel(item.status) }}
                  </span>
                </td>
                <td class="col-actions">
                  <div class="action-group">
                    <button type="button" class="action-btn" @click="goView(item)">
                      {{ t('prompt.view') }}
                    </button>
                    <button type="button" class="action-btn" @click="goEdit(item)">
                      {{ t('prompt.edit') }}
                    </button>
                    <button type="button" class="action-btn" @click="doExport(item)">
                      {{ t('prompt.export') }}
                    </button>
                    <button
                      type="button"
                      class="action-btn"
                      @click="toggleStatus(item)"
                    >
                      {{
                        item.status === 'enabled'
                          ? t('prompt.disable')
                          : t('prompt.enable')
                      }}
                    </button>
                    <button type="button" class="action-btn danger" @click="remove(item)">
                      {{ t('common.delete') }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <PromptOperaView
        v-else
        :mode="operaMode"
        :prompt="operaData"
        @back="backToList"
        @save="onOperaSave"
      />
    </template>

    <!-- 测试评估 -->
    <PromptTestView
      v-else
      :prompt-list="list"
      @edit-template="onEditTemplateFromTest"
    />
  </div>
</template>

<style scoped lang="scss">
.prompt-mng {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.prompt-subtabs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 8px;
}

.prompt-subtab-btn {
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

.prompt-list-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  margin-bottom: 4px;
}

.btn-create {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: var(--accent-gradient, linear-gradient(135deg, #22c55e, #16a34a));
  color: var(--button-text, #fff);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.btn-create:hover {
  opacity: 0.9;
}

.prompt-table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.prompt-loading {
  padding: 40px 24px;
  text-align: center;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.prompt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.prompt-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.prompt-table th,
.prompt-table td {
  padding: 10px 14px;
  text-align: left;
}

.prompt-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.prompt-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.prompt-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.col-name {
  width: 20%;
}

.col-version {
  width: 8%;
}

.col-category {
  width: 12%;
  white-space: nowrap;
}

.col-time {
  width: 14%;
  white-space: nowrap;
}

.col-status {
  width: 10%;
  white-space: nowrap;
}

.col-actions {
  width: 24%;
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

.status-tag {
  font-size: 0.85rem;
}

.status-tag.enabled {
  color: #4ade80;
}

.status-tag.draft {
  color: #a5b4fc;
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
