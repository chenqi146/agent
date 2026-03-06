import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const currentConversationId = ref(null)
  const messages = ref([])
  const streaming = ref(false)
  const lastMessage = ref(null)
  const abortController = ref(null)

  const hasMessages = computed(() => messages.value.length > 0)
  const currentConversation = computed(() => 
    conversations.value.find(c => c.conversationId === currentConversationId.value)
  )

  async function loadHistory() {
    try {
      const res = await chatApi.getHistory()
      if (res.data && res.data.code === 0 && res.data.data) {
        conversations.value = res.data.data.conversations || []
      }
    } catch (e) {
      console.error('Failed to load history:', e)
    }
  }

  async function loadConversation(id) {
    if (currentConversationId.value === id && messages.value.length > 0) return
    
    currentConversationId.value = id
    messages.value = [] // Clear previous messages first
    
    try {
      const res = await chatApi.getConversation(id)
      if (res.data && res.data.code === 0 && res.data.data) {
        messages.value = res.data.data.messages || []
        // Update conversation details if needed
        if (res.data.data.conversation) {
          const idx = conversations.value.findIndex(c => c.conversationId === id)
          if (idx !== -1) {
            conversations.value[idx] = res.data.data.conversation
          } else {
            conversations.value.unshift(res.data.data.conversation)
          }
        }
      }
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }

  async function createConversation(title) {
    // Usually handled by backend on first message, but we can optimistically add one
    // or just reset current ID to null to indicate new chat
    currentConversationId.value = null
    messages.value = []
  }

  async function sendMessage({ message, attachments = [] }) {
    // Add user message immediately
    const userMsg = {
      id: 'temp-' + Date.now(),
      role: 'user',
      content: message,
      attachments,
      createdAt: new Date().toISOString()
    }
    messages.value.push(userMsg)
    
    streaming.value = true
    
    // Create new AbortController
    if (abortController.value) {
      abortController.value.abort()
    }
    abortController.value = new AbortController()

    // Placeholder for assistant message
    const assistantMsg = {
      id: 'temp-ai-' + Date.now(),
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString()
    }
    messages.value.push(assistantMsg)
    lastMessage.value = assistantMsg

    try {
      await chatApi.sendMessageStream({
        message,
        conversationId: currentConversationId.value,
        attachments: attachments.map(a => ({
          fileName: a.fileName,
          fileType: a.fileType,
          fileSize: a.fileSize,
          fileUrl: a.fileUrl,
          storageType: a.storageType || 'local'
        }))
      }, (chunk) => {
        if (chunk.conversationId) {
          currentConversationId.value = chunk.conversationId
          // Update conversation list if it's new
          if (!conversations.value.find(c => c.conversationId === chunk.conversationId)) {
             loadHistory() // Refresh history to get the new one
          }
        }
        if (chunk.content) {
          assistantMsg.content += chunk.content
        }
        if (chunk.error) {
          assistantMsg.content += `\n[Error: ${chunk.error}]`
        }
      }, {
        signal: abortController.value.signal
      })
    } catch (e) {
      if (e.name === 'AbortError') {
        assistantMsg.content += `\n[Aborted]`
      } else {
        console.error('Send message failed:', e)
        assistantMsg.content += `\n[Failed to send message]`
      }
    } finally {
      streaming.value = false
      lastMessage.value = null
      abortController.value = null
      // Reload conversation to get final state/IDs
      if (currentConversationId.value) {
        // Optional: reload to get real IDs, but might flicker. 
        // For now, let's just keep the accumulated content.
      }
    }
  }

  async function deleteConversation(id) {
    try {
      await chatApi.deleteConversation(id)
      conversations.value = conversations.value.filter(c => c.conversationId !== id)
      if (currentConversationId.value === id) {
        currentConversationId.value = null
        messages.value = []
      }
    } catch (e) {
      console.error(e)
    }
  }

  function clearMessages() {
    messages.value = []
    currentConversationId.value = null
  }

  async function stopGeneration() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    
    if (currentConversationId.value) {
      try {
        await chatApi.stopChat(currentConversationId.value)
      } catch (e) {
        console.error('Failed to stop chat:', e)
      }
    }
    
    streaming.value = false
  }

  return {
    conversations,
    currentConversationId,
    messages,
    streaming,
    lastMessage,
    hasMessages,
    currentConversation,
    loadHistory,
    loadConversation,
    createConversation,
    sendMessage,
    stopGeneration,
    deleteConversation,
    clearMessages
  }
})
