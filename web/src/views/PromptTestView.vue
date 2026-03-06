<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { promptApi } from '@/api/prompt'
import { useAuthStore } from '@/store/auth'

const props = defineProps({
  /** 提示词模版列表，用于 A/B 与一键测试的下拉 */
  promptList: { type: Array, default: () => [] }
})

const emit = defineEmits(['edit-template'])

const { t } = useI18n()
const authStore = useAuthStore()

const abPromptAId = ref('')
const abPromptBId = ref('')
const abInput = ref('')
const abResult = ref(null)
const abStreamResultA = ref('')
const abStreamResultB = ref('')
const isAbTesting = ref(false)

const batchPromptId = ref('')
const batchFile = ref(null)
const batchFileName = ref('')
const batchResult = ref(null)

const oneClickPromptId = ref('')
const oneClickInput = ref('')
const oneClickResult = ref(null)
const quickStreamResult = ref('')
const isQuickTesting = ref(false)

const templateA = computed(() =>
  props.promptList.find((p) => p.id === abPromptAId.value)
)
const templateB = computed(() =>
  props.promptList.find((p) => p.id === abPromptBId.value)
)

async function runAbTest() {
  if (!abPromptAId.value || !abPromptBId.value) {
    alert(t('prompt.test.selectTemplatePlaceholder'))
    return
  }

  if (!authStore.token) {
    alert('Authentication token missing. Please login again.')
    return
  }
  
  abStreamResultA.value = ''
  abStreamResultB.value = ''
  // Clear other results
  quickStreamResult.value = ''
  
  isAbTesting.value = true
  
  try {
    const response = await fetch('/api/v1/agent/prompt/test/ab_run_stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`,
        'X-User-Id': String(authStore.userId)
      },
      body: JSON.stringify({
        data: {
          templateAId: abPromptAId.value,
          templateBId: abPromptBId.value,
          inputText: abInput.value
        }
      })
    })
    
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized: Please login again.')
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk
      
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep incomplete line
      
      for (const line of lines) {
        if (!line.trim()) continue
        try {
           const data = JSON.parse(line)
           if (data.tag === 'A') {
             if (data.chunk) abStreamResultA.value += data.chunk
             if (data.error) abStreamResultA.value += '\nError: ' + data.error
           } else if (data.tag === 'B') {
             if (data.chunk) abStreamResultB.value += data.chunk
             if (data.error) abStreamResultB.value += '\nError: ' + data.error
           }
        } catch (e) {
           console.error('JSON parse error', e)
        }
      }
    }
  } catch (e) {
    console.error(e)
    alert('Test Failed: ' + e.message)
  } finally {
    isAbTesting.value = false
  }
}

function onBatchFileChange(e) {
  const file = e.target.files?.[0]
  if (file) {
    batchFile.value = file
    batchFileName.value = file.name
  } else {
    batchFile.value = null
    batchFileName.value = ''
  }
}

async function runBatchTest() {
  if (!batchPromptId.value) {
    alert(t('prompt.test.selectTemplatePlaceholder'))
    return
  }
  if (!batchFile.value) {
    alert(t('prompt.test.uploadTestSet') + '：请先选择 JSON 文件')
    return
  }
  
  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const json = JSON.parse(e.target.result)
      // Assume json is array of cases or object with cases
      const cases = Array.isArray(json) ? json : (json.cases || [])
      
      const res = await promptApi.runBatchTest({
        templateId: batchPromptId.value,
        cases: cases.map((c, i) => ({
          index: i + 1,
          inputData: c.input || c.inputData,
          variables: c.variables,
          expectedOutput: c.output || c.expectedOutput
        }))
      })
      if (res.data && res.data.code === 0 && res.data.data) {
        batchResult.value = res.data.data
        alert('Batch Test Started: ' + (res.data.data.test?.status || 'Success'))
      } else {
        alert('Batch Test Failed: Invalid response')
      }
    } catch (err) {
      console.error(err)
      alert('Invalid JSON or Upload Failed')
    }
  }
  reader.readAsText(batchFile.value)
}

async function runOneClickTest() {
  if (!oneClickPromptId.value) {
    alert(t('prompt.test.selectTemplatePlaceholder'))
    return
  }

  if (!authStore.token) {
    alert('Authentication token missing. Please login again.')
    return
  }
  
  quickStreamResult.value = ''
  // Clear other results
  abStreamResultA.value = ''
  abStreamResultB.value = ''
  
  isQuickTesting.value = true
  
  try {
    const response = await fetch('/api/v1/agent/prompt/test/quick_run_stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`,
        'X-User-Id': String(authStore.userId)
      },
      body: JSON.stringify({
        data: {
          templateId: oneClickPromptId.value,
          inputText: oneClickInput.value
        }
      })
    })

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized: Please login again.')
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      quickStreamResult.value += decoder.decode(value, { stream: true })
    }
  } catch (e) {
    console.error(e)
    alert('Stream Test Failed: ' + e.message)
  } finally {
    isQuickTesting.value = false
  }
}

function editTemplate(item) {
  if (item) emit('edit-template', item)
}
</script>

<template>
  <div class="prompt-test">
    <h2 class="test-heading">{{ t('prompt.test.title') }}</h2>

    <div class="test-cards">
      <!-- A/B 测试：选择不同模版，可编辑 -->
      <div class="test-card">
        <h3 class="test-card-title">{{ t('prompt.test.abTest') }}</h3>
        <p class="test-card-desc">{{ t('prompt.test.abDesc') }}</p>
        <div class="test-card-body">
          <div class="field-row">
            <label>{{ t('prompt.test.selectPromptA') }}</label>
            <div class="select-with-edit">
              <select v-model="abPromptAId" class="test-select">
                <option value="">{{ t('prompt.test.selectTemplatePlaceholder') }}</option>
                <option v-for="p in promptList" :key="p.id" :value="p.id">{{ p.name }} (v{{ p.version || '1.0.0' }})</option>
              </select>
              <button
                v-if="templateA"
                type="button"
                class="btn-edit"
                @click="editTemplate(templateA)"
              >
                {{ t('prompt.test.editTemplate') }}
              </button>
            </div>
          </div>
          <div class="field-row">
            <label>{{ t('prompt.test.selectPromptB') }}</label>
            <div class="select-with-edit">
              <select v-model="abPromptBId" class="test-select">
                <option value="">{{ t('prompt.test.selectTemplatePlaceholder') }}</option>
                <option v-for="p in promptList" :key="p.id" :value="p.id">{{ p.name }} (v{{ p.version || '1.0.0' }})</option>
              </select>
              <button
                v-if="templateB"
                type="button"
                class="btn-edit"
                @click="editTemplate(templateB)"
              >
                {{ t('prompt.test.editTemplate') }}
              </button>
            </div>
          </div>
          <div class="field-row">
            <label>{{ t('prompt.test.testInput') }}</label>
            <textarea
              v-model="abInput"
              class="test-textarea"
              rows="3"
              :placeholder="t('prompt.test.testInputPlaceholder')"
            />
          </div>
          <button type="button" class="btn-run" @click="runAbTest" :disabled="isAbTesting">
            {{ isAbTesting ? 'Testing...' : t('prompt.test.abTest') }}
          </button>
        </div>
      </div>

      <!-- 批量测试：上传 JSON 测试集 -->
      <div class="test-card">
        <h3 class="test-card-title">{{ t('prompt.test.batchTest') }}</h3>
        <p class="test-card-desc">{{ t('prompt.test.uploadTestSetDesc') }}</p>
        <div class="test-card-body">
          <div class="field-row">
            <label>{{ t('prompt.test.selectTemplate') }}</label>
            <select v-model="batchPromptId" class="test-select">
              <option value="">{{ t('prompt.test.selectTemplatePlaceholder') }}</option>
              <option v-for="p in promptList" :key="p.id" :value="p.id">{{ p.name }} (v{{ p.version || '1.0.0' }})</option>
            </select>
          </div>
          <div class="field-row">
            <label>{{ t('prompt.test.uploadTestSet') }}</label>
            <input
              type="file"
              accept=".json,application/json"
              class="file-input"
              :placeholder="t('prompt.test.jsonFilePlaceholder')"
              @change="onBatchFileChange"
            />
            <span v-if="batchFileName" class="file-name">{{ batchFileName }}</span>
          </div>
          <button type="button" class="btn-run" @click="runBatchTest">
            {{ t('prompt.test.batchTest') }}
          </button>
        </div>
      </div>

      <!-- 一键测试 -->
      <div class="test-card">
        <h3 class="test-card-title">{{ t('prompt.test.oneClickTest') }}</h3>
        <p class="test-card-desc">{{ t('prompt.test.oneClickDesc') }}</p>
        <div class="test-card-body">
          <div class="field-row">
            <label>{{ t('prompt.test.selectTemplate') }}</label>
            <select v-model="oneClickPromptId" class="test-select">
              <option value="">{{ t('prompt.test.selectTemplatePlaceholder') }}</option>
              <option v-for="p in promptList" :key="p.id" :value="p.id">{{ p.name }} (v{{ p.version || '1.0.0' }})</option>
            </select>
          </div>
          <div class="field-row">
            <label>{{ t('prompt.test.testInput') }}</label>
            <textarea
              v-model="oneClickInput"
              class="test-textarea"
              rows="3"
              :placeholder="t('prompt.test.testInputPlaceholder')"
            />
          </div>
          <button type="button" class="btn-run" @click="runOneClickTest" :disabled="isQuickTesting">
            {{ isQuickTesting ? 'Testing...' : t('prompt.test.oneClickTest') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Test Results -->
    <div class="test-results" v-if="quickStreamResult || abStreamResultA || abStreamResultB">
      <h3 class="result-title">{{ t('prompt.test.resultTitle') || '测试结果' }}</h3>
      
      <!-- Quick Test Result -->
      <div v-if="quickStreamResult" class="result-box">
         <h4>{{ t('prompt.test.oneClickTest') }} 结果</h4>
         <pre>{{ quickStreamResult }}</pre>
      </div>

      <!-- A/B Test Result -->
      <div v-if="abStreamResultA || abStreamResultB" class="result-ab-container">
         <div class="result-box half">
            <h4>模版 A 结果</h4>
            <pre>{{ abStreamResultA }}</pre>
         </div>
         <div class="result-box half">
            <h4>模版 B 结果</h4>
            <pre>{{ abStreamResultB }}</pre>
         </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.test-results {
  margin-top: 24px;
  background-color: #fff;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

  .result-title {
    font-size: 18px;
    margin-bottom: 16px;
    color: #333;
    font-weight: bold;
  }

  .result-box {
    background: #f5f7fa;
    padding: 16px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    overflow-x: auto;
    
    h4 {
      margin-top: 0;
      margin-bottom: 8px;
      font-size: 14px;
      color: #606266;
      font-weight: bold;
    }
    
    pre {
      margin: 0;
      white-space: pre-wrap;
      font-family: monospace;
      font-size: 14px;
      color: #333;
      line-height: 1.5;
    }
  }

  .result-ab-container {
    display: flex;
    gap: 16px;
    
    .half {
      flex: 1;
    }
  }
}

.prompt-test {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.test-heading {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.test-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.test-card {
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.test-card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.test-card-desc {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin: 0;
}

.test-card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-row {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text-secondary);
  }
}

.select-with-edit {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.test-select {
  flex: 1;
  min-width: 140px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.btn-edit {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.82rem;
  cursor: pointer;
  flex-shrink: 0;
}

.btn-edit:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.test-textarea {
  width: 100%;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-primary);
  font-size: 0.85rem;
  resize: vertical;
  font-family: inherit;
}

.file-input {
  font-size: 0.85rem;
  color: var(--text-primary);
  padding: 6px 0;
}

.file-input::file-selector-button {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 0.85rem;
  cursor: pointer;
  margin-right: 10px;
}

.file-name {
  font-size: 0.85rem;
  color: var(--text-muted);
  margin-top: 4px;
}

.btn-run {
  align-self: flex-start;
  padding: 8px 18px;
  border-radius: 8px;
  border: none;
  background: var(--accent-gradient, linear-gradient(135deg, #22c55e, #16a34a));
  color: var(--button-text, #fff);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-run:hover {
  opacity: 0.9;
}
</style>
