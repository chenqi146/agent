import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatApi } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const conversations = ref([])
  const currentConversationId = ref(null)
  const loading = ref(false)
  const streaming = ref(false)
  const error = ref(null)
  const abortController = ref(null)
  
  // Computed properties
  const hasMessages = computed(() => messages.value.length > 0)
  const lastMessage = computed(() => messages.value.length > 0 ? messages.value[messages.value.length - 1] : null)
  const currentConversation = computed(() => 
    conversations.value.find(c => c.conversationId === currentConversationId.value)
  )

  // Helper to format date
  const formatDate = (date) => new Date(date).toISOString()

  // Actions
  function addMessage(message) {
    messages.value.push({
      id: message.id || Date.now().toString(),
      timestamp: message.timestamp || formatDate(new Date()),
      ...message
    })
  }

  function updateLastMessage(content) {
    if (messages.value.length > 0) {
      const last = messages.value[messages.value.length - 1]
      last.content += content
    }
  }

  function updateLastMessageThinking(content) {
    if (messages.value.length > 0) {
      const last = messages.value[messages.value.length - 1]
      if (!last.thinking) last.thinking = ''
      last.thinking += content
    }
  }

  async function sendMessage(content, attachments = [], thinking = false, roleId = null) {
    if ((!content?.trim() && (!attachments || attachments.length === 0)) || streaming.value) return

    // Optimistically add user message
    const userMsgId = Date.now().toString()
    addMessage({
      id: userMsgId,
      role: 'user',
      content: content?.trim() || '',
      attachments: attachments
    })

    // Prepare assistant message placeholder
    const assistantMsgId = (Date.now() + 1).toString()
    const assistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      thinking: ''
    }
    if (thinking) {
      assistantMsg.thinkingStartTime = Date.now()
    }
    addMessage(assistantMsg)

    streaming.value = true
    error.value = null
    abortController.value = new AbortController()

    try {
      await chatApi.sendMessageStream(
        {
          message: content?.trim(),
          conversationId: currentConversationId.value,
          thinking,
          roleId,
          attachments: attachments.map(a => ({
            id: a.id,
            fileName: a.fileName,
            fileType: a.fileType,
            fileSize: a.fileSize,
            fileUrl: a.fileUrl,
            storageType: a.storageType || 'local',
            thumbnailUrl: a.thumbnailUrl,
            metadata: a.metadata
          }))
        },
        (chunk) => {
          // Handle streaming chunk
          if (chunk.thinking) {
            updateLastMessageThinking(chunk.thinking)
          }
          if (chunk.thinking_duration) {
            const last = messages.value[messages.value.length - 1]
            if (last) {
              last.thinkingDuration = chunk.thinking_duration
            }
          }
          if (chunk.content) {
            // Check if thinking just finished
            const last = messages.value[messages.value.length - 1]
            if (last && last.thinkingStartTime && !last.thinkingDuration) {
              last.thinkingDuration = (Date.now() - last.thinkingStartTime) / 1000
            }
            updateLastMessage(chunk.content)
          }
          if (chunk.conversationId) {
            // Update conversation ID if it was a new chat
            if (currentConversationId.value !== chunk.conversationId) {
                currentConversationId.value = chunk.conversationId
                // Refresh history to show new conversation in sidebar
                loadHistory() 
            }
          }
          if (chunk.error) {
             console.error('Stream error:', chunk.error)
             error.value = chunk.error
          }
        },
        { signal: abortController.value.signal }
      )
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Generation stopped by user')
      } else {
        console.error('Send message failed:', err)
        error.value = err.message || 'Failed to send message'
        // Optionally remove the empty assistant message or show error in it
        if (lastMessage.value?.role === 'assistant' && !lastMessage.value?.content) {
           messages.value.pop()
           addMessage({
              role: 'system',
              content: 'Error: ' + error.value
           })
        }
      }
    } finally {
      streaming.value = false
      abortController.value = null
    }
  }

  async function stopGeneration() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }

    // Check if last message is assistant's and is empty
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
      lastMsg.content = '已停止'
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

  async function loadHistory() {
    loading.value = true
    try {
      const response = await chatApi.getHistory()
      // API returns { code: 0, data: { conversations: [...] } }
      if (response.data && response.data.code === 0 && response.data.data) {
        conversations.value = response.data.data.conversations || []
      } else {
        conversations.value = []
      }
    } catch (err) {
      console.error('Load history failed:', err)
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function loadConversation(conversationId) {
    if (currentConversationId.value === conversationId && messages.value.length > 0) return
    
    currentConversationId.value = conversationId
    loading.value = true
    messages.value = [] // Clear current messages
    
    try {
      const response = await chatApi.getConversation(conversationId)
      // API returns { code: 0, data: { conversation: {}, messages: [] } }
      if (response.data && response.data.code === 0 && response.data.data) {
        messages.value = response.data.data.messages || []
        // Optionally update conversation details if needed
      } else {
        messages.value = []
      }
    } catch (err) {
      console.error('Load conversation failed:', err)
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function deleteConversation(conversationId) {
    try {
      await chatApi.deleteConversation(conversationId)
      // Remove from list
      conversations.value = conversations.value.filter(c => c.conversationId !== conversationId)
      // If current conversation is deleted, clear messages
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = null
        messages.value = []
      }
    } catch (err) {
      console.error('Delete conversation failed:', err)
      error.value = err.message
    }
  }

  async function clearHistory() {
    try {
      await chatApi.clearHistory()
      conversations.value = []
      currentConversationId.value = null
      messages.value = []
    } catch (err) {
        console.error('Clear history failed:', err)
        error.value = err.message
    }
  }

  function createNewChat() {
    currentConversationId.value = null
    messages.value = []
    error.value = null
  }

  return {
    messages,
    conversations,
    currentConversationId,
    loading,
    streaming,
    error,
    hasMessages,
    lastMessage,
    currentConversation,
    sendMessage,
    stopGeneration,
    loadHistory,
    loadConversation,
    deleteConversation,
    clearHistory,
    createNewChat
  }
})
