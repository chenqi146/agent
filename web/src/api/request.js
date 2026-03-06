import axios from 'axios'
import { useAuthStore } from '@/store/auth'
import router from '@/router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
request.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    // agent-service 等接口必须带 X-User-Id，否则 401（store → localStorage → JWT 兜底）
    let userId = authStore.user?.id
    if (userId == null && authStore.token) {
      try {
        const raw = localStorage.getItem('user')
        if (raw) {
          const parsed = JSON.parse(raw)
          if (parsed?.id != null) userId = parsed.id
        }
      } catch (_) {}
    }
    
    if (userId == null && authStore.token) {
      try {
        // Handle Base64Url (replace - with +, _ with /)
        const base64Url = authStore.token.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const payload = JSON.parse(atob(base64))
        if (payload.userId != null) userId = payload.userId
        else if (payload.sub != null) userId = payload.sub
      } catch (e) {
        console.error('Failed to parse token in interceptor:', e)
      }
    }
    if (userId != null) {
      config.headers['X-User-Id'] = String(userId)
    } else {
      console.warn('⚠️ [API] X-User-Id is missing in request headers', config.url)
    }
    // 添加网关 API key
    config.headers['X-API-Key'] = 'pg-gateway-key'

    // 如果是FormData，删除Content-Type让axios自动设置
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
request.interceptors.response.use(
  (response) => {
    // 检查返回的code，所有非0的code都视为错误
    const data = response.data
    if (data && data.code !== undefined && data.code !== 0) {
      const errorMsg = data.message || 'Request failed'
      console.error('❌ [API] Request failed with code:', data.code, 'message:', errorMsg)
      const error = new Error(errorMsg)
      error.response = response
      error.code = data.code
      return Promise.reject(error)
    }
    return response
  },
  (error) => {
    if (error.response) {
      const { status, config } = error.response
      // 只在非 history 和 rag 相关请求的 401 错误时自动登出
      const isExcludedPath = config?.url?.includes('/history') || 
                            config?.url?.includes('/rag') ||
                            config?.url?.includes('/agent/generate')
      if (status === 401 && !isExcludedPath) {
        const authStore = useAuthStore()
        authStore.logout()
        router.push('/login')
      }
    }
    return Promise.reject(error)
  }
)

export default request

