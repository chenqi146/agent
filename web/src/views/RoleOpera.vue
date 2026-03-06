<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { promptApi } from '@/api/prompt'

const props = defineProps({
  /** create | view */
  mode: { type: String, default: 'create' },
  /** 查看/编辑时传入的角色数据 */
  role: { type: Object, default: null }
})

const emit = defineEmits(['back', 'save'])

const { t } = useI18n()

const isView = computed(() => props.mode === 'view')

// 角色名称
const name = ref('')

// 启用时间：开始、结束（HH:mm）
const enableTimeStart = ref('08:00')
const enableTimeEnd = ref('22:00')

// 启用周期：开始、结束日期（YYYY-MM-DD）
const enablePeriodStart = ref('')
const enablePeriodEnd = ref('')

// Prompt：选择已有 或 自定义编辑
const promptMode = ref('select') // select | custom
const selectedPromptId = ref('')
const customPrompt = ref('')

// 角色模型：fixed | dynamic
const roleModel = ref('fixed')
// 固定模式规则：[{ start, end, promptId }]
const fixedRules = ref([])
// 动态模式Prompt IDs
const dynamicPromptIds = ref([])
// 动态模式UI辅助数组: [{ promptId: 1 }, { promptId: 2 }]
const dynamicPromptsUI = ref([])

const promptList = ref([])

let uid = 0
const getUid = () => `rule-${Date.now()}-${uid++}`

onMounted(async () => {
  try {
    const res = await promptApi.list({ page: 1, size: 100 })
    if (res.data && res.data.code === 0 && res.data.data) {
      promptList.value = res.data.data.items || []
    }
  } catch (e) {
    console.error(e)
  }
})

const enableTimeDisplay = computed(() => {
  return `${enableTimeStart.value} - ${enableTimeEnd.value}`
})

const enablePeriodDisplay = computed(() => {
  if (!enablePeriodStart.value || !enablePeriodEnd.value) return ''
  return `${enablePeriodStart.value} 至 ${enablePeriodEnd.value}`
})

const selectedPrompt = computed(() =>
  promptList.value.find((p) => p.id === selectedPromptId.value)
)

function initFromRole() {
  if (!props.role) return
  name.value = props.role.name || ''
  if (props.role.enableTime) {
    const m = props.role.enableTime.match(/(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})/)
    if (m) {
      enableTimeStart.value = m[1]
      enableTimeEnd.value = m[2]
    }
  }
  if (props.role.enablePeriod) {
    const m = props.role.enablePeriod.match(/(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})/)
    if (m) {
      enablePeriodStart.value = m[1]
      enablePeriodEnd.value = m[2]
    }
  }
  if (props.role.promptId) {
    selectedPromptId.value = props.role.promptId
    promptMode.value = 'select'
  }
  if (props.role.customPrompt) {
    customPrompt.value = props.role.customPrompt
    promptMode.value = 'custom'
  }
  
  if (props.role.mode) {
    roleModel.value = props.role.mode
  }
  
  if (props.role.fixedPrompts && props.role.fixedPrompts.length > 0) {
    fixedRules.value = props.role.fixedPrompts.map(r => ({
      _id: getUid(),
      start: r.startTime || r.start || '08:00',
      end: r.endTime || r.end || '22:00',
      promptId: r.promptId
    }))
  } else if (roleModel.value === 'fixed' && props.role.promptId) {
    // Legacy migration to Fixed
    fixedRules.value = [{
      _id: getUid(),
      start: enableTimeStart.value,
      end: enableTimeEnd.value,
      promptId: props.role.promptId
    }]
  }

  if (props.role.dynamicPrompts && props.role.dynamicPrompts.length > 0) {
    dynamicPromptIds.value = props.role.dynamicPrompts
    dynamicPromptsUI.value = props.role.dynamicPrompts.map(pid => ({ _id: getUid(), promptId: pid }))
  } else {
    dynamicPromptsUI.value = []
  }
}

watch(
  () => props.role,
  (r) => {
    if (r) initFromRole()
  },
  { immediate: true }
)

function goBack() {
  emit('back')
}

function submit() {
  // Validate prompt selection
  if (roleModel.value === 'fixed') {
    if (fixedRules.value.some(r => !r.promptId)) {
      alert(t('role.errorPromptRequired', '请为所有时间段选择Prompt'))
      return
    }
  } else if (roleModel.value === 'dynamic') {
    if (dynamicPromptsUI.value.some(item => !item.promptId)) {
      alert(t('role.errorPromptRequired', '请为所有条目选择Prompt'))
      return
    }
  } else if (promptMode.value === 'select' && !selectedPromptId.value) {
    alert(t('role.errorPromptRequired', '请选择Prompt'))
    return
  }

  const payload = {
    name: name.value.trim(),
    enableTime: enableTimeDisplay.value,
    enablePeriod: enablePeriodDisplay.value,
    promptId: promptMode.value === 'select' ? (selectedPromptId.value || null) : null,
    customPrompt: promptMode.value === 'custom' ? customPrompt.value : '',
    mode: roleModel.value,
    fixedPrompts: roleModel.value === 'fixed' ? fixedRules.value.map(r => ({
      startTime: r.start,
      endTime: r.end,
      promptId: r.promptId
    })) : [],
    dynamicPrompts: roleModel.value === 'dynamic' ? dynamicPromptsUI.value.map(item => item.promptId).filter(id => id) : []
  }
  emit('save', payload)
}

function addFixedRule() {
  fixedRules.value.push({ _id: getUid(), start: '08:00', end: '22:00', promptId: '' })
}

function removeFixedRule(index) {
  fixedRules.value.splice(index, 1)
}

function addDynamicPrompt() {
  dynamicPromptsUI.value.push({ _id: getUid(), promptId: '' })
}

function removeDynamicPrompt(index) {
  dynamicPromptsUI.value.splice(index, 1)
}
</script>

<template>
  <div class="role-opera">
    <div class="opera-header">
      <button
        type="button"
        class="btn-back"
        :aria-label="t('role.back', '返回')"
        @click="goBack"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9" />
          <polyline points="13.5 8 9.5 12 13.5 16" />
          <line x1="15" y1="12" x2="9.5" y2="12" />
        </svg>
      </button>
      <h3 class="opera-title">
        {{ isView ? t('role.detailTitle', '角色详情') : t('role.create', '创建角色') }}
      </h3>
    </div>

    <div class="opera-body">
      <!-- 角色名称 -->
      <div class="field-group">
        <label class="field-label">{{ t('role.columns.name', '角色名称') }}</label>
        <input
          v-if="!isView"
          v-model="name"
          type="text"
          class="text-input"
          :placeholder="t('role.namePlaceholder', '请输入角色名称')"
        />
        <div v-else class="field-value">{{ role?.name || '—' }}</div>
      </div>

      <!-- 角色模型 -->
      <div class="field-group">
        <label class="field-label">{{ t('role.model', '角色模型') }}</label>
        <div v-if="!isView" class="radio-group">
          <label class="radio-item">
            <input v-model="roleModel" type="radio" value="fixed" />
            <span>{{ t('role.modeFixed', '固定模式') }}</span>
          </label>
          <label class="radio-item">
            <input v-model="roleModel" type="radio" value="dynamic" />
            <span>{{ t('role.modeDynamic', '动态模式') }}</span>
          </label>
        </div>
        <div v-else class="field-value">
          {{ roleModel === 'fixed' ? t('role.modeFixed', '固定模式') : t('role.modeDynamic', '动态模式') }}
        </div>
      </div>

      <!-- 启用时间 (仅动态模式显示) -->
      <div v-if="false" class="field-group">
        <label class="field-label">{{ t('role.columns.enableTime', '启用时间') }}</label>
        <p v-if="!isView" class="field-hint">{{ t('role.enableTimeHint', '一天内几点到几点') }}</p>
        <div v-if="!isView" class="time-range">
          <input v-model="enableTimeStart" type="time" class="text-input time-input" />
          <span class="time-sep">—</span>
          <input v-model="enableTimeEnd" type="time" class="text-input time-input" />
        </div>
        <div v-else class="field-value">{{ role?.enableTime || '—' }}</div>
      </div>

      <!-- 启用周期 -->
      <div class="field-group">
        <label class="field-label">{{ t('role.columns.enablePeriod', '启用周期') }}</label>
        <p v-if="!isView" class="field-hint">{{ t('role.enablePeriodHint', '开始日期至结束日期') }}</p>
        <div v-if="!isView" class="date-range">
          <input v-model="enablePeriodStart" type="date" class="text-input date-input" />
          <span class="date-sep">至</span>
          <input v-model="enablePeriodEnd" type="date" class="text-input date-input" />
        </div>
        <div v-else class="field-value">{{ role?.enablePeriod || '—' }}</div>
      </div>

      <!-- Prompt 配置 -->
      <div class="field-group">
        <label class="field-label">{{ t('role.promptLabel', 'Prompt') }}</label>
        
        <!-- 固定模式：时间段列表 -->
        <template v-if="roleModel === 'fixed'">
          <div v-if="!isView" class="fixed-rules-editor">
            <div v-for="(rule, idx) in fixedRules" :key="rule._id || idx" class="rule-row">
              <input v-model="rule.start" type="time" class="text-input time-input-sm" />
              <span class="sep">-</span>
              <input v-model="rule.end" type="time" class="text-input time-input-sm" />
              <select v-model="rule.promptId" class="select-input rule-select">
                <option value="" disabled>选择Prompt</option>
                <option v-for="p in promptList" :key="p.id" :value="p.id">
                  {{ p.name }} (v{{ p.version || '1.0.0' }})
                </option>
              </select>
              <button class="btn-icon-del" @click="removeFixedRule(idx)" title="删除">
                ✕
              </button>
            </div>
            <button class="btn-add-rule" @click="addFixedRule">+ 添加时间段规则</button>
          </div>
          <div v-else class="fixed-rules-view">
             <div v-for="(rule, idx) in fixedRules" :key="rule._id || idx" class="rule-item">
               {{ rule.start }} - {{ rule.end }} : {{ promptList.find(p => p.id === rule.promptId)?.name || 'Unknown' }} (v{{ promptList.find(p => p.id === rule.promptId)?.version || '1.0.0' }})
             </div>
          </div>
        </template>

        <!-- 动态模式：多选 (改为列表形式) -->
        <template v-else-if="roleModel === 'dynamic'">
          <div v-if="!isView" class="dynamic-editor">
            <div v-for="(item, idx) in dynamicPromptsUI" :key="item._id || idx" class="rule-row">
              <select v-model="item.promptId" class="select-input rule-select">
                 <option value="" disabled>选择Prompt</option>
                 <option v-for="p in promptList" :key="p.id" :value="p.id">
                   {{ p.name }} (v{{ p.version || '1.0.0' }})
                 </option>
              </select>
              <button class="btn-icon-del" @click="removeDynamicPrompt(idx)" title="删除">
                ✕
              </button>
            </div>
            <button class="btn-add-rule" @click="addDynamicPrompt">+ 添加Prompt</button>
          </div>
          <div v-else class="dynamic-view">
            <span v-for="pid in dynamicPromptIds" :key="pid" class="tag">
              {{ promptList.find(p => p.id === pid)?.name || pid }} (v{{ promptList.find(p => p.id === pid)?.version || '1.0.0' }})
            </span>
          </div>
        </template>

        <!-- Fallback/Legacy UI hidden or removed -->
      </div>
    </div>

    <div v-if="!isView" class="opera-actions">
      <button type="button" class="btn-secondary" @click="goBack">
        {{ t('common.cancel', '取消') }}
      </button>
      <button type="button" class="btn-primary" @click="submit">
        {{ t('common.save', '保存') }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.role-opera {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 200px;
}

.opera-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-back {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, color 0.2s;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  svg {
    width: 18px;
    height: 18px;
  }
}

.opera-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.opera-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
}

.field-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0;
}

.field-value {
  font-size: 0.9rem;
  color: var(--text-secondary);
  padding: 8px 0;
}

.text-input,
.select-input {
  max-width: 360px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.9rem;

  &::placeholder {
    color: var(--text-muted);
  }
}

.text-area {
  max-width: 560px;
  min-height: 120px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.9rem;
  resize: vertical;

  &::placeholder {
    color: var(--text-muted);
  }
}

.time-range,
.date-range {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.time-input {
  width: 120px;
}

.date-input {
  width: 160px;
}

.time-sep,
.date-sep {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.radio-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.radio-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  cursor: pointer;

  input {
    accent-color: var(--accent-color, #22c55e);
  }
}

.prompt-preview {
  .prompt-name {
    display: block;
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 6px;
  }

  .prompt-content {
    margin: 0;
    font-size: 0.85rem;
    color: var(--text-secondary);
    white-space: pre-wrap;
    word-break: break-word;
    background: rgba(15, 23, 42, 0.6);
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--border-primary);
  }
}

.opera-actions {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}

.btn-secondary {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.btn-primary {
  padding: 8px 20px;
  border-radius: 8px;
  border: none;
  background: var(--accent-gradient, linear-gradient(135deg, #22c55e, #16a34a));
  color: var(--button-text, #fff);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.9;
  }
}

.rule-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.time-input-sm {
  width: 100px;
}

.rule-select {
  flex: 1;
}

.btn-icon-del {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 16px;
  padding: 4px;
}

.btn-add-rule {
  color: #3b82f6;
  background: none;
  border: 1px dashed #3b82f6;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  width: 100%;
  margin-top: 8px;
}

.btn-add-rule:hover {
  background: #eff6ff;
}

.multi-select {
  height: 120px;
  width: 100%;
}

.tag {
  display: inline-block;
  background: #e5e7eb;
  padding: 2px 8px;
  border-radius: 4px;
  margin-right: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  color: #333;
}
</style>
