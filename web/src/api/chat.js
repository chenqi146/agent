import request from './request'
import routesConfig from '@/router/routes.json'

const apiRoutes = routesConfig.api.chat

export const chatApi = {
  /**
   * Send message to AI agent
   * @param {Object} data - { message, conversationId? }
   * @returns {Promise} - { response, conversationId }
   */
  sendMessage(data) {
    return request.post(apiRoutes.message, data)
  },

  /**
   * Send message with streaming response
   * @param {Object} data - { message, conversationId? }
   * @param {Function} onMessage - Callback for each chunk
   * @returns {Promise}
   */
  async sendMessageStream(data, onMessage, options = {}) {
    const token = localStorage.getItem('token')
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    let userId = user.id
    
    // Fallback to token payload if userId is missing
    if (!userId && token) {
      try {
        const base64Url = token.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const payload = JSON.parse(atob(base64))
        userId = payload.userId || payload.sub
      } catch (e) {
        console.error('Failed to parse token for userId', e)
      }
    }

    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'api-key': 'pg-gateway-key'
    }
    
    if (userId) {
      headers['X-User-Id'] = String(userId)
    }

    const response = await fetch(`/api${apiRoutes.stream}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      signal: options.signal
    })

    if (!response.ok) {
      throw new Error('Stream request failed')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      
      // Keep the last partial line in the buffer
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (!line.trim()) continue
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            return
          }
          try {
            const parsed = JSON.parse(data)
            onMessage(parsed)
          } catch (e) {
            onMessage({ content: data })
          }
        }
      }
    }
  },

  /**
   * Stop generation
   * @param {string} conversationId
   * @returns {Promise}
   */
  stopChat(conversationId) {
    return request.post(apiRoutes.stop, { conversationId })
  },

  /**
   * Upload file
   * @param {FormData} formData - { file }
   * @returns {Promise} - { url, ... }
   */
  uploadFile(formData) {
    return request.post(apiRoutes.upload, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  /**
   * Get chat history list
   * @returns {Promise} - { conversations: [] }
   */
  getHistory() {
    return request.get(apiRoutes.history)
  },

  /**
   * Get conversation details and messages
   * @param {string} conversationId
   * @returns {Promise} - { conversation: {}, messages: [] }
   */
  getConversation(conversationId) {
    return request.get(`${apiRoutes.conversation}/${conversationId}`)
  },

  /**
   * Delete conversation
   * @param {string} conversationId
   * @returns {Promise}
   */
  deleteConversation(conversationId) {
    return request.delete(`${apiRoutes.conversation}/${conversationId}`)
  },

  /**
   * Clear all chat history
   * @returns {Promise}
   */
  clearHistory() {
    return request.delete(apiRoutes.history)
  },


  /**
   * Upload file
   * @param {File} file
   * @returns {Promise} - { fileName, fileUrl, ... }
   */
  uploadFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(apiRoutes.upload, formData)
  },

  /**
   * Get file URL
   * @param {string} filename
   * @returns {string}
   */
  getFileUrl(filename) {
    return `/api${apiRoutes.file}/${filename}`
  }
}
