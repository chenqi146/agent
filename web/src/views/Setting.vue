<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { roleApi } from '@/api/applicationRole'
import RAGSetting from './RAGSetting.vue'
import RAGSettingSubMngView from './RAGSettingSubMngView.vue'
import RAGSettingSubCreateView from './RAGSettingSubCreateView.vue'
import PromptMng from './PromptMng.vue'
import RoleMng from './RoleMng.vue'
import RoleOpera from './RoleOpera.vue'
import MemoryMng from './MemoryMng.vue'
import TaskOrchestration from './TaskOrchestration.vue'
import McpToolsMngView from './McpToolsMngView.vue'
import McpToolsServiceMngView from './McpToolsServiceMngView.vue'
import McpToolRatingView from './McpToolRatingView.vue'
import McpToolRelationView from './McpToolRelationView.vue'
import McpToolVersionView from './McpToolVersionView.vue'
import McpToolDiscoveryView from './McpToolDiscoveryView.vue'
import SkillsConfig from './SkillsConfig.vue'
import DeviceMngView from './DeviceMngView.vue'
import WarnningView from './WarnningView.vue'
import LoggerMngView from './LoggerMngView.vue'
import LoggerAuditView from './LoggerAuditView.vue'

defineProps({
  standalone: { type: Boolean, default: false }
})

const emit = defineEmits(['close'])
const router = useRouter()
const { t } = useI18n()

function goBack() {
  router.push('/chat')
}

// 智能体子菜单（原有的配置项）
const agentTabs = [
  { id: 'rag', labelKey: 'settings.ragSetting', component: RAGSetting },
  { id: 'prompt', labelKey: 'settings.promptMng', component: PromptMng },
  { id: 'role', labelKey: 'settings.roleMng', component: RoleMng },
  { id: 'memory', labelKey: 'settings.memoryMng', component: MemoryMng },
  { id: 'task', labelKey: 'settings.taskOrchestration', component: TaskOrchestration },
  { id: 'mcp', labelKey: 'settings.mcpToolsConfig', component: null },
  { id: 'skills', labelKey: 'settings.skillsConfig', component: SkillsConfig }
]
// 左侧主菜单：智能体 / 设备管理 / 告警管理 / 日志查看
const activeMainMenu = ref('agent')
const activeAgentTab = ref('rag')
const activeAlertTab = ref('realtime') // 实时告警 / 历史告警
const ragSubtab = ref('manage') // manage | create
const roleSubtab = ref('list') // list | create | view
const roleViewData = ref(null)
const mcpSubtab = ref('tools') // tools | service
const logSubtab = ref('mng') // mng | audit

const currentAgentComponent = computed(() => {
  const tab = agentTabs.find((t) => t.id === activeAgentTab.value)
  return tab?.component || agentTabs[0].component
})

// 历史告警简单示例数据
const historyAlerts = ref([
  {
    id: 1,
    name: '温度传感器异常',
    level: 'fatal',
    time: '2024-01-20 10:30:25',
    deviceName: '温度传感器'
  },
  {
    id: 2,
    name: '压力传感器异常',
    level: 'critical',
    time: '2024-01-19 09:15:10',
    deviceName: '压力传感器'
  },
  {
    id: 3,
    name: '湿度传感器异常',
    level: 'normal',
    time: '2024-01-18 16:42:00',
    deviceName: '湿度传感器'
  },
  {
    id: 4,
    name: '网络连接异常',
    level: 'info',
    time: '2024-01-18 08:05:30',
    deviceName: '边缘网关'
  }
])

function historyAlertLevelText(level) {
  const levelMap = {
    fatal: t('alert.fatal', '致命告警'),
    critical: t('alert.critical', '严重告警'),
    normal: t('alert.normal', '一般告警'),
    info: t('alert.info', '提示告警')
  }
  return levelMap[level] || level
}

async function onRoleSave(payload) {
  try {
    if (roleViewData.value && roleViewData.value.id) {
      await roleApi.update({
        id: roleViewData.value.id,
        ...payload
      })
    } else {
      await roleApi.create(payload)
    }
    roleSubtab.value = 'list'
    roleViewData.value = null
  } catch (e) {
    console.error(e)
    alert('Save failed: ' + (e.message || 'Unknown error'))
  }
}
</script>

<template>
  <div class="setting-panel">
    <div class="setting-header">
      <div class="setting-logo-wrap">
        <!-- 顶部 LOGO：用 SVG 替代位图，去掉白底 -->
        <svg class="setting-logo" viewBox="0 0 120 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- 左侧圆形标志 -->
          <defs>
            <linearGradient id="settingLogoGrad" x1="8" y1="4" x2="24" y2="28" gradientUnits="userSpaceOnUse">
              <stop stop-color="#22d3ee"/>
              <stop offset="1" stop-color="#6366f1"/>
            </linearGradient>
          </defs>
          <circle cx="16" cy="16" r="12" stroke="url(#settingLogoGrad)" stroke-width="2" />
          <path
            d="M16 9c-3 0-5 2-5 4.8 0 1.9 1.2 3.4 3.1 4.1L16 19l1.9-1.1c1.9-.7 3.1-2.2 3.1-4.1C21 11 19 9 16 9Z"
            fill="url(#settingLogoGrad)"
          />
          <circle cx="13.5" cy="15" r="1.2" fill="#020617"/>
          <circle cx="18.5" cy="15" r="1.2" fill="#020617"/>

          <!-- 右侧标题文字 LOGO（无白底，仅描边+填充） -->
          <g transform="translate(34,7)" fill="none" stroke="#e5e7eb" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
            <!-- P -->
            <path d="M2 18V0h5.5C10.5 0 12 1.4 12 3.7 12 6 10.5 7.5 7.5 7.5H4.5"/>
            <!-- G -->
            <path d="M18.5 3.2A6 6 0 0 1 23 1.5c3.5 0 5.5 2.3 5.5 5.9V9h-4.4"/>
            <path d="M28.5 13.5A6 6 0 0 1 23 15.2c-3.5 0-5.5-2.3-5.5-5.9V8.5"/>
          </g>
        </svg>
      </div>
      <button v-if="standalone" type="button" class="back-btn icon-only" :aria-label="t('settings.backToChat')" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="13 8 9 12 13 16"/>
          <line x1="15" y1="12" x2="9" y2="12"/>
        </svg>
      </button>
      <button v-else type="button" class="close-btn" :aria-label="t('common.cancel')" @click="emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>
    <div class="setting-layout">
      <aside class="setting-sidebar">
        <div class="setting-main-menu">
          <button
            type="button"
            class="main-menu-btn"
            :class="{ active: activeMainMenu === 'agent' }"
            @click="activeMainMenu = 'agent'"
          >
            <span class="main-menu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="12" cy="8" r="3" />
                <path d="M5 19c0-3.3 2.8-6 7-6s7 2.7 7 6" />
              </svg>
            </span>
            <span class="main-menu-label">{{ t('settings.agentCenter') }}</span>
          </button>
          <button
            type="button"
            class="main-menu-btn"
            :class="{ active: activeMainMenu === 'device' }"
            @click="activeMainMenu = 'device'"
          >
            <span class="main-menu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="3" y="4" width="18" height="14" rx="2" />
                <path d="M7 9h10M7 13h6" />
              </svg>
            </span>
            <span class="main-menu-label">{{ t('settings.deviceMng') }}</span>
          </button>
          <button
            type="button"
            class="main-menu-btn"
            :class="{ active: activeMainMenu === 'alert' }"
            @click="activeMainMenu = 'alert'"
          >
            <span class="main-menu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M12 3 3 19h18L12 3Z" />
                <circle cx="12" cy="10.5" r="0.9" fill="currentColor" stroke="none" />
                <path d="M12 13.5v3.2" />
              </svg>
            </span>
            <span class="main-menu-label">{{ t('settings.alertMng') }}</span>
          </button>
          <button
            type="button"
            class="main-menu-btn"
            :class="{ active: activeMainMenu === 'log' }"
            @click="activeMainMenu = 'log'"
          >
            <span class="main-menu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="4" y="3" width="16" height="18" rx="2" />
                <path d="M8 8h8M8 12h5M8 16h6" />
              </svg>
            </span>
            <span class="main-menu-label">{{ t('settings.logMng') }}</span>
          </button>
        </div>

        <div v-if="activeMainMenu === 'agent'" class="setting-submenu">
          <button
            v-for="tab in agentTabs"
            :key="tab.id"
            type="button"
            class="submenu-btn"
            :class="{ active: activeAgentTab === tab.id }"
            @click="activeAgentTab = tab.id"
          >
            <span class="submenu-icon">
              <svg v-if="tab.id === 'rag'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="4" y="5" width="16" height="14" rx="2" />
                <path d="M8 9h8M8 13h5" />
              </svg>
              <svg v-else-if="tab.id === 'prompt'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M5 5h14v10H9l-4 4V5Z" />
              </svg>
              <svg v-else-if="tab.id === 'role'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="9" cy="9" r="3" />
                <path d="M4 19c0-2.8 2-5 5-5" />
                <path d="M17 11v6" />
                <path d="M14 14h6" />
              </svg>
              <svg v-else-if="tab.id === 'memory'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="5" y="4" width="14" height="16" rx="2" />
                <path d="M9 8h6M9 12h4M9 16h3" />
              </svg>
              <svg v-else-if="tab.id === 'task'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M5 6h4l2 3h8" />
                <path d="M5 18h4l2-3h8" />
              </svg>
              <svg v-else-if="tab.id === 'mcp'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="3" y="4" width="18" height="14" rx="2" />
                <path d="M7 9h4M7 13h2" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M5 7h14M5 12h10M5 17h7" />
              </svg>
            </span>
            <span class="submenu-label">{{ t(tab.labelKey) }}</span>
          </button>
        </div>

        <div v-else-if="activeMainMenu === 'alert'" class="setting-submenu">
          <button
            type="button"
            class="submenu-btn"
            :class="{ active: activeAlertTab === 'realtime' }"
            @click="activeAlertTab = 'realtime'"
          >
            <span class="submenu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </span>
            <span class="submenu-label">{{ t('settings.alertRealtime') }}</span>
          </button>
          <button
            type="button"
            class="submenu-btn"
            :class="{ active: activeAlertTab === 'history' }"
            @click="activeAlertTab = 'history'"
          >
            <span class="submenu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
            </span>
            <span class="submenu-label">{{ t('settings.alertHistory') }}</span>
          </button>
        </div>

        <div v-else-if="activeMainMenu === 'log'" class="setting-submenu">
          <button
            type="button"
            class="submenu-btn"
            :class="{ active: logSubtab === 'mng' }"
            @click="logSubtab = 'mng'"
          >
            <span class="submenu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="4" y="3" width="16" height="18" rx="2" />
                <path d="M8 8h8M8 12h5M8 16h6" />
              </svg>
            </span>
            <span class="submenu-label">{{ t('log.tabMng', '日志管理') }}</span>
          </button>
          <button
            type="button"
            class="submenu-btn"
            :class="{ active: logSubtab === 'audit' }"
            @click="logSubtab = 'audit'"
          >
            <span class="submenu-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </span>
            <span class="submenu-label">{{ t('log.tabAudit', '日志审计') }}</span>
          </button>
        </div>
      </aside>

      <div class="setting-body">
        <template v-if="activeMainMenu === 'agent'">
          <!-- 知识库时增加子菜单：知识库管理 / 创建知识库 -->
          <div v-if="activeAgentTab === 'rag'" class="rag-subtabs">
            <button
              type="button"
              class="rag-subtab-btn"
              :class="{ active: ragSubtab === 'manage' }"
              @click="ragSubtab = 'manage'"
            >
              {{ t('rag.tabManage') }}
            </button>
            <button
              type="button"
              class="rag-subtab-btn"
              :class="{ active: ragSubtab === 'create' }"
              @click="ragSubtab = 'create'"
            >
              {{ t('rag.tabCreate') }}
            </button>
          </div>
          <template v-if="activeAgentTab === 'rag'">
            <RAGSettingSubMngView v-if="ragSubtab === 'manage'" />
            <RAGSettingSubCreateView v-else @back-to-manage="ragSubtab = 'manage'" />
          </template>
          <template v-else-if="activeAgentTab === 'role'">
            <RoleMng
              v-if="roleSubtab === 'list'"
              @create="roleSubtab = 'create'; roleViewData = null"
              @view-detail="(r) => { roleViewData = r; roleSubtab = 'view' }"
              @edit="(r) => { roleViewData = r; roleSubtab = 'create' }"
            />
            <RoleOpera
              v-else
              :mode="roleSubtab === 'view' ? 'view' : 'create'"
              :role="roleViewData"
              @back="roleSubtab = 'list'; roleViewData = null"
              @save="onRoleSave"
            />
          </template>
          <template v-else-if="activeAgentTab === 'mcp'">
            <div class="mcp-subtabs">
              <button
                type="button"
                class="mcp-subtab-btn"
                :class="{ active: mcpSubtab === 'tools' }"
                @click="mcpSubtab = 'tools'"
              >
                {{ t('mcp.tabTools') }}
              </button>
              <button
                type="button"
                class="mcp-subtab-btn"
                :class="{ active: mcpSubtab === 'service' }"
                @click="mcpSubtab = 'service'"
              >
                {{ t('mcp.tabService') }}
              </button>
              <button
                type="button"
                class="mcp-subtab-btn"
                :class="{ active: mcpSubtab === 'rating' }"
                @click="mcpSubtab = 'rating'"
              >
                {{ t('mcp.tabRating') }}
              </button>
              <button
                type="button"
                class="mcp-subtab-btn"
                :class="{ active: mcpSubtab === 'relation' }"
                @click="mcpSubtab = 'relation'"
              >
                {{ t('mcp.tabRelation') }}
              </button>
              <button
                type="button"
                class="mcp-subtab-btn"
                :class="{ active: mcpSubtab === 'version' }"
                @click="mcpSubtab = 'version'"
              >
                {{ t('mcp.tabVersion') }}
              </button>
              <button
                type="button"
                class="mcp-subtab-btn"
                :class="{ active: mcpSubtab === 'discovery' }"
                @click="mcpSubtab = 'discovery'"
              >
                {{ t('mcp.tabDiscovery') }}
              </button>
            </div>
            <McpToolsMngView v-if="mcpSubtab === 'tools'" @go-service-config="mcpSubtab = 'service'" />
            <McpToolsServiceMngView v-else-if="mcpSubtab === 'service'" />
            <McpToolRatingView v-else-if="mcpSubtab === 'rating'" />
            <McpToolRelationView v-else-if="mcpSubtab === 'relation'" />
            <McpToolVersionView v-else-if="mcpSubtab === 'version'" />
            <McpToolDiscoveryView v-else-if="mcpSubtab === 'discovery'" />
          </template>
          <component
            v-else
            :is="currentAgentComponent"
          />
        </template>
        <template v-else-if="activeMainMenu === 'device'">
          <!-- 设备管理：使用表格模式 -->
          <DeviceMngView :list-mode="true" />
        </template>
        <template v-else-if="activeMainMenu === 'alert'">
          <!-- 告警管理：实时告警 / 历史告警 -->
          <WarnningView v-if="activeAlertTab === 'realtime'" :hide-title="true" />
          <div v-else class="history-alert-wrapper">
            <h3 class="history-alert-title">{{ t('alert.historyTitle', '历史告警') }}</h3>
            <div class="history-alert-table">
              <div class="history-alert-header">
                <div class="col-time">{{ t('alert.time', '告警时间') }}</div>
              <div class="col-device">{{ t('alert.deviceName', '告警设备名称') }}</div>
              <div class="col-content">{{ t('alert.content', '告警内容') }}</div>
                <div class="col-level">{{ t('alert.level', '告警等级') }}</div>
                <div class="col-action">{{ t('alert.action', '操作') }}</div>
              </div>
              <div
                v-for="item in historyAlerts"
                :key="item.id"
                class="history-alert-row"
              >
                <div class="col-time">{{ item.time }}</div>
                <div class="col-device">{{ item.deviceName }}</div>
                <div class="col-content">{{ item.name }}</div>
                <div class="col-level">
                  <span class="history-alert-level" :class="item.level">
                    {{ historyAlertLevelText(item.level) }}
                  </span>
                </div>
                <div class="col-action">
                  <button type="button" class="history-alert-btn">
                    {{ t('alert.view', '查看详情') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </template>
        <template v-else-if="activeMainMenu === 'log'">
          <div class="log-subtabs">
            <button
              type="button"
              class="log-subtab-btn"
              :class="{ active: logSubtab === 'mng' }"
              @click="logSubtab = 'mng'"
            >
              {{ t('log.tabMng') }}
            </button>
            <button
              type="button"
              class="log-subtab-btn"
              :class="{ active: logSubtab === 'audit' }"
              @click="logSubtab = 'audit'"
            >
              {{ t('log.tabAudit') }}
            </button>
          </div>
          <LoggerMngView v-if="logSubtab === 'mng'" />
          <LoggerAuditView v-else />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.setting-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.setting-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.setting-logo-wrap {
  display: flex;
  align-items: center;
}

.setting-logo {
  height: 32px;
  display: block;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 4px;
  font-family: var(--font-primary);
  font-size: 0.9rem;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 28px;
    height: 28px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
    border-color: var(--accent-primary);
  }
}

.close-btn {
  padding: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 8px;
  transition: all 0.2s ease;

  svg {
    width: 20px;
    height: 20px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.setting-layout {
  flex: 1;
  display: flex;
  min-height: 0;
}

.setting-sidebar {
  width: 210px;
  border-right: 1px solid var(--border-primary);
  padding: 16px 16px 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
}

.setting-main-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.main-menu-btn {
  width: 100%;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 1.05rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: transparent;
    color: var(--accent-primary);
    font-weight: 600;
  }
}

.main-menu-icon {
  width: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.main-menu-icon svg {
  width: 18px;
  height: 18px;
}

.setting-submenu {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--border-primary);
}

.submenu-btn {
  width: 100%;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: transparent;
    color: var(--accent-primary);
    font-weight: 600;
  }
}

.submenu-icon {
  width: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.submenu-icon svg {
  width: 16px;
  height: 16px;
}

.setting-body {
  flex: 1;
  overflow: auto;
  padding: 24px;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.setting-body::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.rag-subtabs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px 0;
}

.rag-subtab-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--button-text);
    background: var(--accent-gradient);
  }
}

.mcp-subtabs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px 0;
}

.mcp-subtab-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--button-text);
    background: var(--accent-gradient);
  }
}

.log-subtabs {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px 0;
}

.log-subtab-btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--button-text);
    background: var(--accent-gradient);
  }
}

.history-alert-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-alert-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.history-alert-table {
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  overflow: hidden;
}

.history-alert-header,
.history-alert-row {
  display: grid;
  grid-template-columns: 150px 180px 1fr 110px 110px;
  align-items: center;
  padding: 10px 16px;
  column-gap: 12px;
}

.history-alert-header {
  background: rgba(148, 163, 184, 0.08);
  font-size: 0.8rem;
  color: var(--text-muted);
}

.history-alert-row {
  font-size: 0.85rem;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-primary);
}

.history-alert-level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
}

.history-alert-level.fatal,
.history-alert-level.critical {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.history-alert-level.normal {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.history-alert-level.info {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.history-alert-btn {
  padding: 6px 10px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}
</style>
