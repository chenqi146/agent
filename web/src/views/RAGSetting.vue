<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// 知识库类型
const KB_TYPES = {
  document: 'document',
  vector: 'vector'
}

const list = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const newName = ref('')
const newType = ref(KB_TYPES.document)

function loadList() {
  loading.value = true
  // 模拟请求，后续可替换为真实 API
  setTimeout(() => {
    list.value = [
      { id: '1', name: '智能管家产品文档库', type: KB_TYPES.document, createdAt: '2025-01-15 10:00', totalCapacity: '256 MB', fileCount: 12, enabled: true },
      { id: '2', name: '技术知识库', type: KB_TYPES.vector, createdAt: '2025-01-20 14:30', totalCapacity: '512 MB', fileCount: 28, enabled: true },
      { id: '3', name: 'FAQ 库', type: KB_TYPES.document, createdAt: '2025-02-01 09:15', totalCapacity: '128 MB', fileCount: 5, enabled: false }
    ]
    loading.value = false
  }, 300)
}

onMounted(loadList)

function openCreate() {
  newName.value = ''
  newType.value = KB_TYPES.document
  showCreateDialog.value = true
}

function closeCreate() {
  showCreateDialog.value = false
}

function submitCreate() {
  if (!newName.value.trim()) return
  list.value = [
    ...list.value,
    {
      id: String(Date.now()),
      name: newName.value.trim(),
      type: newType.value,
      createdAt: new Date().toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).replace(/\//g, '-'),
      totalCapacity: '0 MB',
      fileCount: 0,
      enabled: true
    }
  ]
  closeCreate()
}

function remove(item) {
  if (!confirm(t('rag.confirmDelete', { name: item.name }))) return
  list.value = list.value.filter((i) => i.id !== item.id)
}

function importKnowledge(item) {
  // 后续对接导入能力
  alert(t('rag.importTip', { name: item.name }))
}

function toggleEnabled(item) {
  item.enabled = !item.enabled
}

function typeLabel(type) {
  return t(`rag.types.${type}`)
}

defineExpose({
  openCreate,
  closeCreate
})
</script>

<template>
  <div class="rag-setting">
    <div class="rag-header">
      <div class="rag-desc-wrap">
        <span class="rag-desc-icon" aria-hidden="true">ℹ</span>
        <span class="rag-desc">{{ t('rag.fileSupportDesc') }}</span>
      </div>
      <button type="button" class="btn-primary" @click="openCreate">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        {{ t('rag.create') }}
      </button>
    </div>

    <div class="rag-table-wrap">
      <div v-if="loading" class="rag-loading">{{ t('common.loading') }}</div>
      <table v-else class="rag-table">
        <thead>
          <tr>
            <th>{{ t('rag.columns.name') }}</th>
            <th>{{ t('rag.columns.type') }}</th>
            <th>{{ t('rag.columns.createdAt') }}</th>
            <th>{{ t('rag.columns.totalCapacity') }}</th>
            <th>{{ t('rag.columns.fileCount') }}</th>
            <th class="col-actions">{{ t('rag.columns.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="list.length === 0">
            <td colspan="6" class="empty-cell">{{ t('common.noData') }}</td>
          </tr>
          <tr v-for="item in list" :key="item.id">
            <td class="col-name">{{ item.name }}</td>
            <td>{{ typeLabel(item.type) }}</td>
            <td class="col-time">{{ item.createdAt }}</td>
            <td class="col-capacity">{{ item.totalCapacity ?? '0 MB' }}</td>
            <td class="col-count">{{ item.fileCount ?? 0 }}</td>
            <td class="col-actions">
              <button type="button" class="action-btn" :title="t('rag.import')" @click="importKnowledge(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <span class="action-text">{{ t('rag.import') }}</span>
              </button>
              <button type="button" class="action-btn" :title="item.enabled ? t('rag.disable') : t('rag.enable')" @click="toggleEnabled(item)">
                <svg v-if="item.enabled" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <span class="action-text">{{ item.enabled ? t('rag.disable') : t('rag.enable') }}</span>
              </button>
              <button type="button" class="action-btn danger" :title="t('common.delete')" @click="remove(item)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
                <span class="action-text">{{ t('common.delete') }}</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 新建知识库弹层 -->
    <Teleport to="body">
      <Transition name="dialog">
        <div v-if="showCreateDialog" class="dialog-overlay" @click.self="closeCreate">
          <div class="dialog-box">
            <h4 class="dialog-title">{{ t('rag.create') }}</h4>
            <div class="dialog-form">
              <label class="form-label">{{ t('rag.columns.name') }}</label>
              <input v-model="newName" type="text" class="form-input" :placeholder="t('rag.namePlaceholder')" />
              <label class="form-label">{{ t('rag.columns.type') }}</label>
              <select v-model="newType" class="form-select">
                <option value="document">{{ t('rag.types.document') }}</option>
                <option value="vector">{{ t('rag.types.vector') }}</option>
              </select>
            </div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="closeCreate">{{ t('common.cancel') }}</button>
              <button type="button" class="btn-primary" :disabled="!newName.trim()" @click="submitCreate">{{ t('common.save') }}</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped lang="scss">
.rag-setting {
  min-height: 200px;
}

.rag-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.rag-desc-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  padding: 10px 14px;
  background: rgba(var(--accent-rgb, 34 197 94), 0.08);
  border: 1px solid rgba(var(--accent-rgb, 34 197 94), 0.2);
  border-radius: 10px;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.rag-desc-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-primary);
  color: var(--bg-primary);
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 600;
}

.rag-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 10px 18px;
  font-family: var(--font-primary);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--button-text);
  background: var(--accent-gradient);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover:not(:disabled) {
    filter: brightness(1.08);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.btn-secondary {
  padding: 10px 18px;
  font-family: var(--font-primary);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.rag-table-wrap {
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-tertiary);
}

.rag-loading {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
}

.rag-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;

  th,
  td {
    padding: 14px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-primary);
  }

  th {
    font-weight: 600;
    color: var(--text-muted);
    background: rgba(0, 0, 0, 0.2);
  }

  tbody tr:last-child td {
    border-bottom: none;
  }

  tbody tr:hover {
    background: var(--bg-hover);
  }

  .col-name {
    font-weight: 500;
    color: var(--text-primary);
  }

  .col-time {
    color: var(--text-secondary);
  }

  .col-capacity,
  .col-count {
    color: var(--text-secondary);
  }

  .col-actions {
    white-space: nowrap;
  }

  .empty-cell {
    text-align: center;
    color: var(--text-muted);
    padding: 32px !important;
  }
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  margin-right: 6px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
  }

  &.danger:hover {
    color: var(--error-text);
  }
}

.action-text {
  @media (max-width: 600px) {
    display: none;
  }
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
  padding: 24px;
}

.dialog-box {
  width: 100%;
  max-width: 400px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow-xl);
}

.dialog-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 20px 0;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.form-input,
.form-select {
  padding: 10px 14px;
  font-family: var(--font-primary);
  font-size: 0.9rem;
  color: var(--text-primary);
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s ease;

  &:focus {
    border-color: var(--accent-primary);
  }
}

.form-select {
  cursor: pointer;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.2s ease;
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}
.dialog-enter-active .dialog-box,
.dialog-leave-active .dialog-box {
  transition: transform 0.2s ease;
}
.dialog-enter-from .dialog-box,
.dialog-leave-to .dialog-box {
  transform: scale(0.98);
}
</style>
