<script setup>
import Setting from './Setting.vue'
</script>

<template>
  <div class="manager-page">
    <Setting standalone />
  </div>
</template>

<style scoped lang="scss">
.manager-page {
  min-height: 100vh;
  height: 100vh;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
}

.manager-page :deep(.setting-panel) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
