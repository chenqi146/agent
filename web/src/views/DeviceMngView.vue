<script setup>
import { ref, computed } from 'vue'

defineProps({
  /** true=弹层内表格列表，false=侧栏内卡片 */
  listMode: { type: Boolean, default: false }
})

// 设备类型选项
const deviceTypes = [
  { value: 'all', label: '全部' },
  { value: 'compute', label: '算力设备' },
  { value: 'camera', label: '摄像头' },
  { value: 'sensor', label: '传感器' },
]

const selectedType = ref('all')

// 设备数据
const devices = ref([
  { id: 1, name: '边缘智能体', type: 'compute', status: 'online', registerTime: '2024-01-15 10:30:00' },
  { id: 2, name: '环境传感器', type: 'sensor', status: 'online', registerTime: '2024-01-15 11:15:00' },
  { id: 3, name: '摄像头', type: 'camera', status: 'offline', registerTime: '2024-01-15 12:00:00' },
  { id: 4, name: '气体传感器', type: 'sensor', status: 'online', registerTime: '2024-01-15 13:30:00' },
  { id: 5, name: '门磁传感器', type: 'sensor', status: 'online', registerTime: '2024-01-15 14:00:00' },
  { id: 6, name: '红外传感器', type: 'sensor', status: 'offline', registerTime: '2024-01-15 14:30:00' },
  { id: 7, name: '户外摄像头', type: 'camera', status: 'online', registerTime: '2024-01-15 15:00:00' },
  { id: 8, name: '室内摄像头', type: 'camera', status: 'online', registerTime: '2024-01-15 15:30:00' },
  { id: 9, name: '温度传感器', type: 'sensor', status: 'online', registerTime: '2024-01-15 16:00:00' },
])

// 计算过滤后的设备列表
const filteredDevices = computed(() => {
  if (selectedType.value === 'all') {
    return devices.value
  }
  return devices.value.filter(device => device.type === selectedType.value)
})

// 切换设备状态
function toggleDeviceStatus(device) {
  device.status = device.status === 'online' ? 'offline' : 'online'
}

// 获取设备类型文本
function getDeviceTypeText(type) {
  const typeMap = {
    compute: '算力设备',
    camera: '摄像头',
    sensor: '传感器',
  }
  return typeMap[type] || type
}

// 获取设备状态文本
function getDeviceStatusText(status) {
  const statusMap = {
    online: '在线',
    offline: '离线'
  }
  return statusMap[status] || status
}
</script>

<template>
  <div class="device-page">
    <div class="device-content">
      <div class="device-section">
        <div v-if="listMode" class="section-header section-header-inline">
          <h3 class="section-title">设备列表</h3>
          <div class="device-type-filter">
            <button
              v-for="type in deviceTypes"
              :key="type.value"
              class="filter-btn"
              :class="{ active: selectedType === type.value }"
              @click="selectedType = type.value"
            >
              {{ type.label }}
            </button>
          </div>
        </div>
        <div v-if="listMode" class="device-table-container">
          <table class="device-table">
            <thead>
              <tr>
                <th>设备名称</th>
                <th>设备类型</th>
                <th>在线状态</th>
                <th>注册时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="device in filteredDevices" :key="device.id">
                <td>{{ device.name }}</td>
                <td>{{ getDeviceTypeText(device.type) }}</td>
                <td>
                  <span class="status-badge" :class="device.status">
                    {{ getDeviceStatusText(device.status) }}
                  </span>
                </td>
                <td>{{ device.registerTime }}</td>
                <td>
                  <button
                    class="action-btn"
                    :class="device.status"
                    @click="toggleDeviceStatus(device)"
                  >
                    {{ device.status === 'online' ? '禁用' : '启用' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="device-card-list">
          <div
            v-for="device in filteredDevices"
            :key="device.id"
            class="device-card"
            :class="{ online: device.status === 'online', offline: device.status === 'offline' }"
          >
            <div class="device-card-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="layers-icon">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div class="device-card-main">
              <div class="device-card-name">{{ device.name }}</div>
              <div class="device-card-status" :class="device.status">
                {{ getDeviceStatusText(device.status) }}
              </div>
            </div>
            <div class="device-card-dot" :class="device.status"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.device-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 40px;
}

.device-header {
  margin-bottom: 32px;
  text-align: center;

  .page-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.device-content {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.device-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;

  .section-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  &.section-header-inline {
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-primary);
    margin-bottom: 12px;
  }
}

.device-type-filter {
  display: flex;
  gap: 8px;

  .filter-btn {
    padding: 6px 12px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: 6px;
    color: var(--text-secondary);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    &.active {
      background: var(--accent-primary);
      border-color: var(--accent-primary);
      color: white;
    }
  }
}

.device-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.device-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  border-left-width: 4px;
  transition: all 0.2s ease;

  &.online {
    background: var(--bg-secondary);
    border-left-color: var(--success-text, #34d399);
  }

  &.offline {
    background: var(--bg-tertiary);
    border-left-color: transparent;
  }
}

.device-card-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);

  svg {
    width: 28px;
    height: 28px;
  }
}

.device-card-main {
  flex: 1;
  min-width: 0;
}

.device-card-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.device-card-status {
  font-size: 0.8rem;
  font-weight: 500;

  &.online {
    color: var(--success-text, #34d399);
  }

  &.offline {
    color: var(--error-text, #ef4444);
  }
}

.device-card-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;

  &.online {
    background: var(--success-text, #34d399);
  }

  &.offline {
    background: var(--error-text, #ef4444);
  }
}

.device-table-container {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  overflow: hidden;
}

.device-table {
  width: 100%;
  border-collapse: collapse;

  thead {
    background: var(--bg-tertiary);

    th {
      padding: 12px 16px;
      text-align: left;
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text-primary);
      border-bottom: 1px solid var(--border-primary);
    }
  }

  tbody {
    tr {
      border-bottom: 1px solid var(--border-primary);

      &:last-child {
        border-bottom: none;
      }

      &:hover {
        background: var(--bg-hover);
      }

      td {
        padding: 12px 16px;
        font-size: 0.875rem;
        color: var(--text-secondary);
      }
    }
  }
}

.status-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;

  &.online {
    background: rgba(52, 211, 153, 0.1);
    color: var(--success-text, #34d399);
  }

  &.offline {
    background: rgba(239, 68, 68, 0.1);
    color: var(--error-text, #ef4444);
  }
}

.action-btn {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
  }

  &.online {
    color: var(--error-text, #ef4444);
    border-color: var(--error-text);

    &:hover {
      background: rgba(239, 68, 68, 0.1);
    }
  }

  &.offline {
    color: var(--success-text, #34d399);
    border-color: var(--success-text);

    &:hover {
      background: rgba(52, 211, 153, 0.1);
    }
  }
}
</style>