<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { promptApi } from '@/api/prompt'
import request from '@/api/request'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/store/auth'

const props = defineProps({
  mode: { type: String, default: 'create' }, // create | view | edit
  prompt: { type: Object, default: null }
})

const emit = defineEmits(['back', 'save'])

const { t } = useI18n()
const isView = computed(() => props.mode === 'view')

const templateName = ref('')
const version = ref('1.0.0')
const category = ref('')
const content = ref('')
const variables = ref([]) // { key, defaultValue, description, required }
const isGenerating = ref(false)
const roleName = ref('') // 角色名称
const wordCount = ref(200) // 生成文字数

function initFromPrompt() {
  if (!props.prompt) return
  templateName.value = props.prompt.name || ''
  version.value = props.prompt.version || '1.0.0'
  category.value = props.prompt.category || ''
  content.value = props.prompt.content || ''
  variables.value = Array.isArray(props.prompt.variables)
    ? props.prompt.variables.map((v) => ({ ...v }))
    : []
  roleName.value = props.prompt.roleName || ''
}

watch(
  () => props.prompt,
  (p) => {
    if (p) initFromPrompt()
  },
  { immediate: true }
)

function insertVariable(varKey) {
  const token = `{{${varKey}}}`
  const textarea = document.getElementById('prompt-content-textarea')
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = content.value.slice(0, start)
    const after = content.value.slice(end)
    content.value = before + token + after
    nextTick(() => {
      textarea.focus()
      const pos = start + token.length
      textarea.setSelectionRange(pos, pos)
    })
  } else {
    content.value += token
  }
}

function addVariable() {
  variables.value.push({
    key: '',
    defaultValue: '',
    description: '',
    required: false
  })
}

function removeVariable(index) {
  variables.value.splice(index, 1)
}

function goBack() {
  emit('back')
}

function submit() {
  emit('save', {
    name: templateName.value.trim(),
    version: version.value.trim(),
    category: category.value,
    content: content.value,
    variables: variables.value.filter((v) => v.key.trim()),
    roleName: roleName.value.trim()
  })
}

function varTag(key) {
  return '\u007B\u007B' + key + '\u007D\u007D'
}

function getCategoryLabel(category) {
  if (!category) return '—'
  const key = `prompt.categories.${category}`
  const label = t(key)
  return label === key ? category : label
}

async function generatePrompt() {
  if (!category.value) {
    message.warning(t('prompt.pleaseSelectCategory'))
    return
  }
  
  if (isGenerating.value) return
  
  isGenerating.value = true
  content.value = '' // Clear content for streaming
  try {
    // 组织发送给agent-service的prompt
    const baseRequirements = [
      '1. 提示词应该清晰、具体、易于理解',
      '2. 包含必要的指令和示例',
      '3. 结构清晰，逻辑严密',
      '4. 适合在实际场景中使用'
    ]

    if (wordCount.value && wordCount.value > 0) {
      baseRequirements.push(`${baseRequirements.length + 1}. 提示词内容长度（不包含示例等）尽量控制在 ${wordCount.value} 字以内`)
    }

    let contextInfo = `类别：${getCategoryLabel(category.value)}`
    if (templateName.value && templateName.value.trim()) {
      contextInfo += `\n提示词模板名称：${templateName.value.trim()}`
    }
    if (roleName.value && roleName.value.trim()) {
      contextInfo += `\n目标角色：${roleName.value.trim()}`
    }

    const promptText = `你是一个专业的提示词工程师。请根据以下信息生成一个高质量的提示词模板：

${contextInfo}

要求：
${baseRequirements.join('\n')}

请直接输出提示词内容，不要包含任何解释或说明。`
    
    // 调用/v1/agent/generate/stream接口生成提示词 (流式)
    const authStore = useAuthStore()
    const token = authStore.token
    
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'X-API-Key': 'pg-gateway-key'
    }
    
    if (authStore.user?.id) {
        headers['X-User-Id'] = String(authStore.user.id)
    }

    const response = await fetch('/api/v1/agent/generate/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message: promptText,
        conversationId: null,
        thinking: false,
        attachments: []
      })
    })

    if (!response.ok) {
        const errorText = await response.text()
        let errorMsg = t('prompt.generateFailed')
        try {
            const errorJson = JSON.parse(errorText)
            if (errorJson.message) errorMsg = errorJson.message
        } catch (_) {}
        throw new Error(errorMsg)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (!line.trim()) continue
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            message.success(t('prompt.generateSuccess'))
            return
          }
          try {
            const parsed = JSON.parse(data)
            if (parsed.content !== undefined) {
                content.value += parsed.content
                // Auto scroll to bottom if needed, but textarea usually handles it or user scrolls
                const textarea = document.getElementById('prompt-content-textarea')
                if (textarea) {
                    textarea.scrollTop = textarea.scrollHeight
                }
            } else if (parsed.error) {
                throw new Error(parsed.error)
            }
          } catch (e) {
             console.error('Error parsing SSE data:', e)
          }
        }
      }
    }
    
  } catch (e) {
    console.error('Generate Prompt Error:', e)
    message.error(e.message || t('prompt.generateFailed'))
  } finally {
    isGenerating.value = false
  }
}
</script>

<template>
  <div class="prompt-opera">
    <div class="opera-header">
      <button type="button" class="btn-back" :aria-label="t('prompt.back')" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9" />
          <polyline points="13.5 8 9.5 12 13.5 16" />
          <line x1="15" y1="12" x2="9.5" y2="12" />
        </svg>
      </button>
      <h3 class="opera-title">
        {{ isView ? t('prompt.view') : (mode === 'edit' ? t('prompt.edit') : t('prompt.create')) }}
      </h3>
    </div>

    <div class="opera-body">
      <div class="field-group input-row">
        <div class="input-col flex-grow">
          <label class="field-label">{{ t('prompt.templateName') }}</label>
          <input
            v-if="!isView"
            v-model="templateName"
            type="text"
            class="text-input full-width"
            :placeholder="t('prompt.templateNamePlaceholder')"
          />
          <div v-else class="field-value">{{ prompt?.name || '—' }}</div>
        </div>
        <div class="input-col w-150">
          <label class="field-label">{{ t('prompt.version') }}</label>
          <input
            v-if="!isView"
            v-model="version"
            type="text"
            class="text-input full-width"
            placeholder="1.0.0"
          />
          <div v-else class="field-value">{{ prompt?.version || '1.0.0' }}</div>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">{{ t('prompt.category') }}</label>
        <div class="category-input-wrapper">
          <select
            v-if="!isView"
            v-model="category"
            class="select-input"
          >
            <option value="">{{ t('prompt.categoryPlaceholder') }}</option>
            <option value="general">{{ t('prompt.categories.general') }}</option>
            <option value="instruction">{{ t('prompt.categories.instruction') }}</option>
            <option value="qa">{{ t('prompt.categories.qa') }}</option>
            <option value="judgment">{{ t('prompt.categories.judgment') }}</option>
            <option value="reasoning">{{ t('prompt.categories.reasoning') }}</option>
            <option value="summary">{{ t('prompt.categories.summary') }}</option>
            <option value="roleplay">{{ t('prompt.categories.roleplay') }}</option>
          </select>
          <input
            v-if="!isView && category === 'roleplay'"
            v-model="roleName"
            type="text"
            class="text-input role-name-input"
            :placeholder="t('请出入角色名称')"
          />
          <div v-else-if="isView" class="field-value">{{ getCategoryLabel(prompt?.category) }}</div>
          <div v-if="isView && prompt?.category === 'roleplay'" class="field-value">{{ prompt?.roleName || '—' }}</div>
        </div>
      </div>

      <div class="field-group">
        <label class="field-label">{{ t('prompt.content') }}</label>
        <textarea
          v-if="!isView"
          id="prompt-content-textarea"
          v-model="content"
          class="content-textarea"
          rows="10"
          :placeholder="t('prompt.contentPlaceholder')"
        />
        <div v-else class="field-value content-preview">
          <pre>{{ prompt?.content || '—' }}</pre>
        </div>
        <div class="generate-wrapper">
          <button
            v-if="!isView"
            type="button"
            class="btn-generate"
            :disabled="isGenerating"
            @click="generatePrompt"
          >
            {{ isGenerating ? t('prompt.generating') : t('prompt.generateBtn') }}
          </button>
          <div v-if="!isView" class="word-count-input">
            <label class="word-count-label">{{ t('约束字数') }}</label>
            <input
              v-model.number="wordCount"
              type="number"
              class="text-input word-count-number"
              min="50"
              max="1000"
              step="50"
            />
          </div>
        </div>
        <p v-if="!isView && variables.length" class="insert-hint">
          {{ t('prompt.insertVariableHint') }}
        </p>
      </div>

      <div class="field-group">
        <label class="field-label">{{ t('prompt.variableManagement') }}</label>
        <template v-if="!isView">
          <button type="button" class="btn-add-var" @click="addVariable">
            {{ t('prompt.addVariable') }}
          </button>
          <table class="var-table">
            <thead>
              <tr>
                <th>{{ t('prompt.dynamicVar') }}</th>
                <th>{{ t('prompt.defaultValue') }}</th>
                <th>{{ t('prompt.description') }}</th>
                <th>{{ t('prompt.required') }}</th>
                <th class="col-actions"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="variables.length === 0">
                <td colspan="5" class="empty-cell">{{ t('common.noData') }}</td>
              </tr>
              <tr v-for="(v, index) in variables" :key="index">
                <td>
                  <input
                    v-model="v.key"
                    type="text"
                    class="var-input"
                    :placeholder="t('prompt.dynamicVar')"
                  />
                  <button
                    v-if="v.key.trim()"
                    type="button"
                    class="btn-insert-tag"
                    :title="varTag(v.key)"
                    @click="insertVariable(v.key)"
                  >
                    {{ varTag(v.key) }}
                  </button>
                </td>
                <td>
                  <input v-model="v.defaultValue" type="text" class="var-input" />
                </td>
                <td>
                  <input v-model="v.description" type="text" class="var-input" />
                </td>
                <td>
                  <label class="checkbox-label">
                    <input v-model="v.required" type="checkbox" />
                    <span>{{ v.required ? t('prompt.requiredYes') : t('prompt.requiredNo') }}</span>
                  </label>
                </td>
                <td class="col-actions">
                  <button type="button" class="action-btn danger" @click="removeVariable(index)">
                    {{ t('common.delete') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </template>
        <template v-else>
          <div v-if="prompt?.variables?.length" class="var-list-view">
            <div
              v-for="(v, i) in prompt.variables"
              :key="i"
              class="var-item"
            >
              <span class="var-key">{{ v.key }}</span>
              <span class="var-meta">{{ v.defaultValue }} · {{ v.description || '—' }} · {{ v.required ? t('prompt.requiredYes') : t('prompt.requiredNo') }}</span>
            </div>
          </div>
          <div v-else class="field-value">—</div>
        </template>
      </div>
    </div>

    <div v-if="!isView" class="opera-actions">
      <button type="button" class="btn-secondary" @click="goBack">{{ t('common.cancel') }}</button>
      <button type="button" class="btn-primary" @click="submit">{{ t('common.save') }}</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.prompt-opera {
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  gap: 8px;
}

.input-row {
  display: flex;
  flex-direction: row;
  gap: 12px;
  width: 100%;
  max-width: 720px;
}

.input-col {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.flex-grow {
  flex: 1;
}

.w-150 {
  width: 150px;
}

.full-width {
  width: 100%;
  max-width: none !important;
}

.field-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
}

.field-value {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.text-input,
.select-input {
  max-width: 400px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.category-input-wrapper {
  display: flex;
  gap: 12px;
  align-items: center;
}

.role-name-input {
  flex: 1;
  max-width: 300px;
}

.content-textarea {
  width: 100%;
  max-width: 720px;
  min-height: 200px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.9rem;
  resize: vertical;
  font-family: inherit;
}

.btn-generate {
  width: 90px;
  padding: 6px 12px;
  border-radius: 6px;
  border: none;
  background: var(--accent-gradient, linear-gradient(135deg, #22c55e, #16a34a));
  color: var(--button-text, #fff);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s ease;
  white-space: nowrap;
  margin-top: 8px;
}

.generate-wrapper {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 8px;
}

.word-count-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.word-count-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.word-count-number {
  width: 80px;
  padding: 6px 8px;
}

.btn-generate:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.content-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 10px 12px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid var(--border-primary);
}

.insert-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin: 0;
}

.btn-add-var {
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
}

.btn-add-var:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.var-table {
  width: 100%;
  max-width: 800px;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.var-table th,
.var-table td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid var(--border-primary);
}

.var-table th {
  font-weight: 500;
  color: var(--text-muted);
  background: rgba(15, 23, 42, 0.6);
}

.var-table .col-actions {
  width: 80px;
}

.var-input {
  width: 100%;
  min-width: 80px;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 0.85rem;
}

.btn-insert-tag {
  margin-left: 6px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid rgba(56, 189, 248, 0.5);
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-insert-tag:hover {
  background: rgba(56, 189, 248, 0.3);
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  cursor: pointer;
}

.var-list-view {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.var-item {
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-primary);
  font-size: 0.85rem;
}

.var-key {
  font-weight: 500;
  color: var(--text-primary);
  margin-right: 8px;
}

.var-meta {
  color: var(--text-muted);
}

.empty-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 16px;
}

.opera-actions {
  display: flex;
  gap: 12px;
}

.btn-secondary {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
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
}

.btn-primary:hover {
  opacity: 0.9;
}

.action-btn.danger {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(248, 113, 113, 0.6);
  background: transparent;
  color: #fecaca;
  font-size: 0.8rem;
  cursor: pointer;
}
</style>
