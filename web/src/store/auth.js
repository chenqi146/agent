import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

// Token刷新间隔（秒），设置为30分钟
const REFRESH_INTERVAL = 30 * 60

export const useAuthStore = defineStore('auth', () => {
  // 从localStorage初始化token和user，之后只通过store操作
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)
  
  // 初始化时从localStorage加载用户数据
  try {
    const userData = localStorage.getItem('user')
    if (userData !== null && userData !== '' && userData !== undefined) {
      user.value = JSON.parse(userData)
    }
  } catch (e) {
    console.error('Failed to parse user data from localStorage:', e)
    user.value = null
    // 如果解析失败，清除无效的localStorage数据
    localStorage.removeItem('user')
  }
  
  const loading = ref(false)
  const error = ref(null)
  let refreshTimer = null

  const isAuthenticated = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')
  const userId = computed(() => user.value?.id || user.value?.userId || '')

  async function login(credentials) {
    console.log('🔐 [AUTH] Login attempt:', credentials)
    
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.login(credentials)
      console.log('✅ [AUTH] Login response:', response)
      
      // 处理API响应数据，兼容不同的响应格式
      // request.js的响应拦截器返回完整的response对象
      const data = response.data?.data || response.data
      
      console.log('✅ [AUTH] Login success:', data)
      
      // 从后端返回的数据中提取 token 和用户信息
      if (data.token) {
        token.value = data.token
        localStorage.setItem('token', data.token)
      }
      
      user.value = {
        id: data.userId || data.user?.id,
        username: data.username || data.user?.username,
        roles: data.roles || data.user?.roles || []
      }
      
      localStorage.setItem('user', JSON.stringify(user.value))
      
      // Start token refresh timer
      startTokenRefresh()
      
      return response
    } catch (err) {
      console.error('❌ [AUTH] Login failed:', err)
      error.value = err.response?.data?.message || 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      if (token.value) {
        // 先调用后端logout接口，传递token
        await authApi.logout(token.value)
      }
    } catch (err) {
      // Ignore logout errors
      console.error('Logout API call failed:', err)
    } finally {
      // 停止token刷新定时器
      stopTokenRefresh()
      
      // 清除store中的token和user
      token.value = null
      user.value = null
      
      // 清除localStorage中的token和user
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }

  async function refreshToken() {
    try {
      const response = await authApi.refreshToken()
      const data = response.data?.data || response.data
      
      if (data.token) {
        token.value = data.token
        localStorage.setItem('token', data.token)
      }
      return data
    } catch (err) {
      console.error('Token refresh failed:', err)
      // If refresh fails, we might want to logout or just let the token expire
    }
  }

  function startTokenRefresh() {
    stopTokenRefresh()
    refreshTimer = setInterval(() => {
      refreshToken()
    }, REFRESH_INTERVAL * 1000)
  }

  function stopTokenRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    username,
    userId,
    login,
    logout,
    refreshToken
  }
})
