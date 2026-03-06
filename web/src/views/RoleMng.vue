<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { roleApi } from '@/api/applicationRole'

const { t } = useI18n()

const emit = defineEmits(['create', 'view-detail', 'edit'])

const list = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const size = ref(10)

async function loadList() {
  loading.value = true
  try {
    const res = await roleApi.list({
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

function openDetail(item) {
  emit('view-detail', item)
}

function openEdit(item) {
  emit('edit', item)
}

async function toggleEnabled(item) {
  try {
    const newStatus = !item.enabled
    await roleApi.toggleStatus(item.id, newStatus)
    item.enabled = newStatus
  } catch (e) {
    console.error(e)
  }
}

async function remove(item) {
  if (!window.confirm(t('role.confirmDelete', { name: item.name }))) return
  try {
    await roleApi.delete(item.id)
    loadList()
  } catch (e) {
    console.error(e)
  }
}

function createRole() {
  emit('create')
}
</script>

<template>
  <div class="role-mng">
    <div class="role-header">
      <div>
        <h2 class="page-heading">{{ t('role.listTitle', '角色列表') }}</h2>
      </div>
      <button type="button" class="btn-create-role" @click="createRole">
        {{ t('role.create') }}
      </button>
    </div>

    <div class="role-table-wrap">
      <div v-if="loading" class="role-loading">{{ t('common.loading') }}</div>
      <table v-else class="role-table">
        <thead>
          <tr>
            <th>{{ t('role.columns.name') }}</th>
            <th>{{ t('role.columns.createdAt') }}</th>
            <th>{{ t('role.columns.enableTime') }}</th>
            <th>{{ t('role.columns.enablePeriod') }}</th>
            <th class="col-actions">{{ t('role.columns.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="list.length === 0">
            <td colspan="5" class="empty-cell">{{ t('common.noData') }}</td>
          </tr>
          <tr v-for="item in list" :key="item.id">
            <td class="col-name">{{ item.name }}</td>
            <td class="col-time">{{ item.createdAt }}</td>
            <td class="col-enable-time">{{ item.enableTime }}</td>
            <td class="col-enable-period">{{ item.enablePeriod }}</td>
            <td class="col-actions">
              <div class="action-group">
                <button type="button" class="action-btn" @click="openDetail(item)">
                  {{ t('role.viewDetail') }}
                </button>
                <button type="button" class="action-btn" @click="openEdit(item)">
                  {{ t('common.edit', '编辑') }}
                </button>
                <button
                  type="button"
                  class="action-btn"
                  :class="{ active: item.enabled }"
                  @click="toggleEnabled(item)"
                >
                  {{ item.enabled ? t('role.disable') : t('role.enable') }}
                </button>
                <button type="button" class="action-btn danger" @click="remove(item)">
                  {{ t('role.delete') }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.role-mng {
  min-height: 200px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.role-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 4px;
}

.page-heading {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  letter-spacing: 0.01em;
}

.btn-create-role {
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  background: var(--accent-gradient, linear-gradient(135deg, #22c55e, #16a34a));
  color: var(--button-text, #fff);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.btn-create-role:hover {
  opacity: 0.9;
}

.role-table-wrap {
  border-radius: 14px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.role-loading {
  padding: 40px 24px;
  text-align: center;
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.role-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  table-layout: fixed;
}

.role-table thead {
  background: rgba(15, 23, 42, 0.8);
}

.role-table th,
.role-table td {
  padding: 10px 14px;
  text-align: left;
  width: 20%;
  box-sizing: border-box;
}

.role-table th {
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-primary);
}

.role-table tbody tr:nth-child(even) {
  background: rgba(15, 23, 42, 0.6);
}

.role-table tbody tr:hover {
  background: rgba(15, 23, 42, 0.9);
}

.role-table .col-name,
.role-table .col-time,
.role-table .col-enable-time,
.role-table .col-enable-period {
  overflow: hidden;
  text-overflow: ellipsis;
}

.role-table .col-time {
  white-space: nowrap;
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
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    border-color: rgba(34, 197, 94, 0.6);
    color: #86efac;
  }

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
