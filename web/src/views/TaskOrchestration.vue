<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="task-orchestration">
    <h3 class="page-title">{{ t('settings.taskOrchestration') }}</h3>
    <p class="page-desc">{{ t('common.noData') }}</p>
  </div>
</template>

<style scoped lang="scss">
.task-orchestration {
  min-height: 120px;
}

.page-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.page-desc {
  font-size: 0.9rem;
  color: var(--text-muted);
  margin: 0;
}
</style>
