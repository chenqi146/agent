<template>
  <div class="language-switcher">
    <button
      class="lang-btn"
      :class="{ active: locale === 'zh' }"
      @click="setLocale('zh')"
    >
      中
    </button>
    <button
      class="lang-btn"
      :class="{ active: locale === 'en' }"
      @click="setLocale('en')"
    >
      EN
    </button>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

function setLocale(lang) {
  locale.value = lang
  localStorage.setItem('locale', lang)
}
</script>

<style lang="scss" scoped>
.language-switcher {
  display: flex;
  gap: 4px;
  background: var(--bg-tertiary);
  padding: 4px;
  border-radius: 8px;
}

.lang-btn {
  padding: 6px 12px;
  font-family: var(--font-primary);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover:not(.active) {
    color: var(--text-secondary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--button-text);
    background: var(--accent-gradient);
  }
}
</style>

