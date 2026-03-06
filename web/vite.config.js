import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 18090,
    proxy: {
      '/api': {
        target: 'http://localhost:19082',
        changeOrigin: true,
        configure: (proxy) => {
          // 确保关键请求头被转发到网关（避免被代理丢弃导致 401）
          proxy.on('proxyReq', (proxyReq, req) => {
            const auth = req.headers.authorization
            if (auth) proxyReq.setHeader('Authorization', auth)
            const userId = req.headers['x-user-id']
            if (userId) proxyReq.setHeader('X-User-Id', userId)
            const apiKey = req.headers['x-api-key']
            if (apiKey) proxyReq.setHeader('X-API-Key', apiKey)
          })
        }
      }
    }
  }
})

