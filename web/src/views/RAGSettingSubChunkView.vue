<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface KnowledgeItem {
  id?: number | string
  fileName?: string
  recallCount?: number
  lastAccessTime?: string
  avgScore?: number
  instructionScore?: number
  relevanceScore?: number
  isNoise?: boolean
  isRedundant?: boolean
  createdAt?: string
  updatedAt?: string
}

const { t } = useI18n()

const props = defineProps<{
  kb: any | null
  list: KnowledgeItem[]
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'view', item: KnowledgeItem): void
}>()

const title = computed(() => props.kb?.name || t('rag.knowledgeInfo.title'))

function handleClose() {
  emit('close')
}

function handleView(item: KnowledgeItem) {
  emit('view', item)
}
</script>

<template>
  <div class="chunk-overlay">
    <div class="chunk-panel">
      <div class="chunk-header">
        <button
          type="button"
          class="btn-secondary rag-back-btn"
          :aria-label="t('rag.backToKb')"
          @click="handleClose"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="9" />
            <polyline points="13.5 8 9.5 12 13.5 16" />
            <line x1="15" y1="12" x2="9.5" y2="12" />
          </svg>
        </button>
        <div class="chunk-title">
          <span class="kb-name">{{ title }}</span>
          <span v-if="kb?.id" class="kb-id">ID: {{ kb.id }}</span>
        </div>
      </div>

      <div class="rag-table-wrap">
        <table class="rag-table">
          <thead>
            <tr>
              <th>{{ t('rag.knowledgeInfo.columns.fileName') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.recallCount') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.lastAccess') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.avgScore') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.instructionScore') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.relevanceScore') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.isNoise') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.isRedundant') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.createdAt') }}</th>
              <th>{{ t('rag.knowledgeInfo.columns.updatedAt') }}</th>
              <th class="col-actions">{{ t('rag.knowledgeInfo.columns.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!list || list.length === 0">
              <td colspan="11" class="empty-cell">{{ t('rag.knowledgeInfo.empty') }}</td>
            </tr>
            <tr v-for="item in list" :key="item.id ?? `${item.fileName}-${item.createdAt}`">
              <td class="col-name">{{ item.fileName || '-' }}</td>
              <td>{{ item.recallCount ?? 0 }}</td>
              <td>{{ item.lastAccessTime || '-' }}</td>
              <td>{{ item.avgScore ?? '-' }}</td>
              <td>{{ item.instructionScore ?? '-' }}</td>
              <td>{{ item.relevanceScore ?? '-' }}</td>
              <td>{{ item.isNoise ? t('rag.knowledgeInfo.yes') : t('rag.knowledgeInfo.no') }}</td>
              <td>{{ item.isRedundant ? t('rag.knowledgeInfo.yes') : t('rag.knowledgeInfo.no') }}</td>
              <td>{{ item.createdAt || '-' }}</td>
              <td>{{ item.updatedAt || '-' }}</td>
              <td class="col-actions">
                <button type="button" class="action-btn" @click="handleView(item)">{{ t('common.view') }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chunk-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.85);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 40px 24px;
  z-index: 1000;
}

.chunk-panel {
  width: 100%;
  max-width: 1200px;
  background: var(--bg-tertiary);
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.8);
  overflow: hidden;
}

.chunk-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-primary);
}

.btn-secondary {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.rag-back-btn {
  padding: 4px;

  svg {
    width: 22px;
    height: 22px;
  }
}

.chunk-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-name {
  font-size: 0.95rem;
  color: var(--text-primary);
}

.kb-id {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.rag-table-wrap {
  max-height: 520px;
  overflow: auto;
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.rag-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.rag-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.rag-table th,
.rag-table td {
  padding: 10px 14px;
  text-align: left;
}

.rag-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.rag-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.rag-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.col-name {
  max-width: 260px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.col-actions {
  width: 480px;
  white-space: nowrap;
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px 12px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-right: 6px;

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    border-color: var(--border-primary);
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.danger:hover {
    border-color: rgba(248, 113, 113, 0.6);
    color: #f97373;
  }
}
</style>
