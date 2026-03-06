<template>
  <div class="login-page">
    <div class="login-background">
      <div class="gradient-orb orb-1"></div>
      <div class="gradient-orb orb-2"></div>
      <div class="gradient-orb orb-3"></div>
    </div>
    
    <div class="login-container">
      <div class="login-card">
        <div class="login-header">
          <div class="logo-wrapper">
            <div class="logo-icon">
              <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/>
                <path d="M16 24C16 19.5817 19.5817 16 24 16V16C28.4183 16 32 19.5817 32 24V32H16V24Z" fill="currentColor"/>
                <circle cx="20" cy="26" r="2" fill="var(--bg-primary)"/>
                <circle cx="28" cy="26" r="2" fill="var(--bg-primary)"/>
              </svg>
            </div>
          </div>
          <h1 class="login-title">{{ t('common.appName') }}</h1>
          <p class="login-subtitle">{{ t('auth.enterCredentials') }}</p>
        </div>

        <form class="login-form" @submit.prevent="handleLogin">
          <div class="form-group">
            <label class="form-label">{{ t('auth.username') }}</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <input
                v-model="form.username"
                type="text"
                class="form-input"
                :placeholder="t('auth.username')"
                required
                autocomplete="username"
              />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('auth.password') }}</label>
            <div class="input-wrapper">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input"
                :placeholder="t('auth.password')"
                required
                autocomplete="current-password"
              />
              <button
                type="button"
                class="password-toggle"
                @click="showPassword = !showPassword"
              >
                <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">{{ t('auth.captcha') }}</label>
            <div class="captcha-wrapper">
              <div class="input-wrapper">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <input
                  v-model="form.captcha"
                  type="text"
                  class="form-input"
                  :placeholder="t('auth.enterCaptcha')"
                  maxlength="6"
                  required
                  autocomplete="off"
                />
              </div>
              <div class="captcha-image-container" @click="refreshCaptcha">
                <img v-if="captchaImage" :src="captchaImage" alt="验证码" class="captcha-image" />
                <div v-else class="captcha-loading">{{ t('auth.loadingCaptcha') }}</div>
              </div>
            </div>
            <div class="captcha-hint">
              {{ t('auth.refreshCaptcha') }}
            </div>
          </div>

          <div class="form-options">
            <label class="checkbox-wrapper">
              <input v-model="form.rememberMe" type="checkbox" />
              <span class="checkmark"></span>
              <span>{{ t('auth.rememberMe') }}</span>
            </label>
          </div>

          <button
            type="submit"
            class="login-button"
            :disabled="loading"
          >
            <span v-if="loading" class="loading-spinner"></span>
            <span v-else>{{ t('auth.login') }}</span>
          </button>

          <div v-if="error" class="error-message">
            {{ error }}
          </div>
        </form>

        <div class="login-footer">
          <LanguageSwitcher />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/api/auth'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
  captcha: '',
  rememberMe: false
})

const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const captchaImage = ref('')
const captchaId = ref('')

async function refreshCaptcha() {
  try {
    const res = await authApi.getCaptcha()
    // 后端返回 ApiResult：{ code, message, data: { imageBase64, captchaId, expireSeconds } }
    // request.js的响应拦截器返回完整的response对象
    const data = res?.data?.data || res?.data || res
    captchaImage.value = data?.imageBase64 ? `data:image/png;base64,${data.imageBase64}` : ''
    captchaId.value = data?.captchaId || ''
  } catch (err) {
    console.error('Failed to load captcha:', err)
  }
}

onMounted(() => {
  refreshCaptcha()
})

async function handleLogin() {
  loading.value = true
  error.value = ''

  try {
    await authStore.login({
      username: form.username,
      password: form.password,
      captcha: form.captcha,
      captchaId: captchaId.value
    })
    router.push('/chat')
  } catch (err) {
    // 显示后端返回的具体错误信息
    error.value = err.message || err.response?.data?.message || t('auth.invalidCredentials')
    console.error('Login failed:', err)
    // 登录失败后刷新验证码
    refreshCaptcha()
    form.captcha = ''
  } finally {
    loading.value = false
  }
}

async function handleLogout() {
  try {
    // authStore.logout() 会自动调用 authApi.logout()，并将token通过请求拦截器添加到请求头中
    await authStore.logout()
    // 登出成功后跳转到登录页
    router.push('/login')
  } catch (err) {
    console.error('Logout failed:', err)
    // 即使登出失败，也清除本地状态并跳转到登录页
    router.push('/login')
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  inset: 0;
  background: var(--bg-primary);
  z-index: 0;

  .gradient-orb {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.6;
    animation: float 20s ease-in-out infinite;

    &.orb-1 {
      width: 600px;
      height: 600px;
      background: var(--accent-gradient);
      top: -200px;
      right: -100px;
      animation-delay: 0s;
    }

    &.orb-2 {
      width: 400px;
      height: 400px;
      background: var(--secondary-gradient);
      bottom: -100px;
      left: -50px;
      animation-delay: -7s;
    }

    &.orb-3 {
      width: 300px;
      height: 300px;
      background: var(--tertiary-gradient);
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      animation-delay: -14s;
    }
  }
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(30px, -30px) scale(1.05);
  }
  66% {
    transform: translate(-20px, 20px) scale(0.95);
  }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 440px;
  padding: 20px;
}

.login-card {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  border-radius: 24px;
  padding: 48px 40px;
  box-shadow: var(--shadow-xl);
  animation: slideUp 0.6s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.logo-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  color: var(--accent-primary);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.login-title {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.login-subtitle {
  font-size: 0.95rem;
  color: var(--text-secondary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  pointer-events: none;
}

.form-input {
  width: 100%;
  padding: 14px 16px 14px 48px;
  font-family: var(--font-primary);
  font-size: 1rem;
  color: var(--text-primary);
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: 12px;
  outline: none;
  transition: all 0.2s ease;

  &::placeholder {
    color: var(--text-muted);
  }

  &:focus {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }
}

.password-toggle {
  position: absolute;
  right: 12px;
  padding: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  transition: color 0.2s ease;

  svg {
    width: 20px;
    height: 20px;
  }

  &:hover {
    color: var(--text-secondary);
  }
}

.captcha-wrapper {
  display: flex;
  gap: 12px;
  align-items: center;

  .input-wrapper {
    flex: 1;
  }

  .captcha-image-container {
    flex-shrink: 0;
    width: 120px;
    height: 48px;
  }

  .captcha-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
    border-radius: 8px;
    cursor: pointer;
    transition: transform 0.2s ease;

    &:hover {
      transform: scale(1.05);
    }
  }

  .captcha-loading {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--input-bg);
    border-radius: 8px;
    font-size: 0.875rem;
    color: var(--text-muted);
  }
}

.captcha-hint {
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-secondary);

  input {
    display: none;
  }

  .checkmark {
    width: 18px;
    height: 18px;
    border: 2px solid var(--input-border);
    border-radius: 4px;
    transition: all 0.2s ease;
    position: relative;

    &::after {
      content: '';
      position: absolute;
      left: 5px;
      top: 2px;
      width: 4px;
      height: 8px;
      border: solid var(--bg-primary);
      border-width: 0 2px 2px 0;
      transform: rotate(45deg);
      opacity: 0;
      transition: opacity 0.2s ease;
    }
  }

  input:checked + .checkmark {
    background: var(--accent-primary);
    border-color: var(--accent-primary);

    &::after {
      opacity: 1;
    }
  }
}

.login-button {
  margin-top: 8px;
  padding: 16px;
  font-family: var(--font-primary);
  font-size: 1rem;
  font-weight: 600;
  color: var(--button-text);
  background: var(--accent-gradient);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.2), transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-accent);

    &::before {
      opacity: 1;
    }
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
}

.loading-spinner {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  padding: 12px 16px;
  background: var(--error-bg);
  color: var(--error-text);
  border-radius: 8px;
  font-size: 0.875rem;
  text-align: center;
  animation: shake 0.4s ease;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.login-footer {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--glass-border);
  display: flex;
  justify-content: center;
}
</style>

