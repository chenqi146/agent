<script setup>
import { ref } from 'vue'
import { mcpToolsApi } from '@/api/mcpTools'

const loading = ref(false)
const searchResults = ref([])
const keyword = ref('')

async function searchTools() {
  if (!keyword.value.trim()) {
    alert('请输入关键词')
    return
  }
  try {
    loading.value = true
    const res = await mcpToolsApi.searchTools({ keyword: keyword.value })
    searchResults.value = res.data.items
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mcp-discovery-view">
    <div class="section-header">
      <!-- <h2 class="section-title">工具发现模型</h2> -->
    </div>

    <!-- Search Box -->
    <div class="search-section">
      <input 
        v-model="keyword" 
        type="text" 
        class="search-input" 
        placeholder="搜索工具..." 
        @keyup.enter="searchTools"
      />
      <button class="btn-primary" @click="searchTools" :disabled="loading">
        {{ loading ? '搜索中...' : '搜索' }}
      </button>
    </div>

    <!-- Search Results -->
    <div class="results-section">
      <h3>搜索结果</h3>
      <div v-if="loading">加载中...</div>
      <ul v-else class="results-list">
        <li v-for="tool in searchResults" :key="tool.id" class="result-item">
          <div class="tool-name">{{ tool.name }}</div>
          <div class="tool-desc">{{ tool.description }}</div>
        </li>
        <li v-if="!loading && searchResults.length === 0">暂无结果</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.mcp-discovery-view {
  padding: 20px;
  color: var(--text-primary);
}

.section-header {
  margin-bottom: 20px;
  border-bottom: 1px solid var(--border-primary);
  padding-bottom: 10px;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 600;
}

.search-section {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  padding: 8px;
  border: 1px solid var(--border-primary);
  border-radius: 4px;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn-primary {
  padding: 8px 16px;
  background: var(--accent-primary);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.results-list {
  list-style: none;
  padding: 0;
}

.result-item {
  padding: 10px;
  border-bottom: 1px solid var(--border-primary);
}

.tool-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.tool-desc {
  font-size: 0.9rem;
  color: var(--text-secondary);
}
</style>
