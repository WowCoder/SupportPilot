import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  listSessions,
  createSession,
  listMessages,
  sendMessage,
  closeSession,
  reopenSession,
  markAttention,
  requestHandoff,
} from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  // --- State ---
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const loading = ref(false)
  const sending = ref(false)

  // --- Getters ---
  const currentSession = computed(() =>
    sessions.value.find((s) => s.id === currentSessionId.value) || null
  )

  // --- Actions ---
  async function loadSessions() {
    try {
      const { data } = await listSessions()
      sessions.value = data.data || []
    } catch (err) {
      console.error('Failed to load sessions:', err)
    }
  }

  async function newSession() {
    try {
      const { data } = await createSession()
      const session = data.data
      sessions.value.unshift(session)
      await selectSession(session.id)
      return session
    } catch (err) {
      console.error('Failed to create session:', err)
      throw err
    }
  }

  async function selectSession(sessionId) {
    currentSessionId.value = sessionId
    messages.value = []
    loading.value = true
    try {
      const { data } = await listMessages(sessionId)
      messages.value = data.data?.items || []
    } catch (err) {
      console.error('Failed to load messages:', err)
    } finally {
      loading.value = false
    }
  }

  async function postMessage(content) {
    if (!currentSessionId.value) return
    sending.value = true

    // Optimistic: add user message immediately
    const tempUserMsg = {
      id: Date.now(),
      conversation_id: currentSessionId.value,
      sender_type: 'user',
      content,
      timestamp: new Date().toISOString(),
      _optimistic: true,
    }
    messages.value.push(tempUserMsg)

    // Add AI thinking placeholder
    const thinkingId = Date.now() + 1
    const thinkingMsg = {
      id: thinkingId,
      conversation_id: currentSessionId.value,
      sender_type: 'ai',
      content: 'AI 正在思考...',
      timestamp: new Date().toISOString(),
      _thinking: true,
    }
    messages.value.push(thinkingMsg)

    try {
      const { data } = await sendMessage(currentSessionId.value, content)
      // Remove thinking placeholder
      messages.value = messages.value.filter((m) => !m._thinking)
      // Replace optimistic message with real data
      const idx = messages.value.findIndex((m) => m._optimistic)
      if (idx >= 0) {
        messages.value[idx] = data.data.user_message
        delete messages.value[idx]._optimistic
      }
      // Add AI response if present
      if (data.data.ai_message) {
        const aiMsg = { ...data.data.ai_message }
        if (data.data.rag_metadata) {
          aiMsg._rag_metadata = data.data.rag_metadata
        }
        messages.value.push(aiMsg)
      } else if (data.data.ai_error) {
        // Show AI unavailable message
        messages.value.push({
          id: Date.now(),
          conversation_id: currentSessionId.value,
          sender_type: 'ai',
          content: `⚠️ ${data.data.ai_error}`,
          timestamp: new Date().toISOString(),
        })
      }
    } catch (err) {
      // Remove optimistic and thinking messages on failure
      messages.value = messages.value.filter((m) => !m._optimistic && !m._thinking)
      console.error('Failed to send message:', err)
      throw err
    } finally {
      sending.value = false
    }
  }

  async function closeCurrentSession(generateFaq = false) {
    if (!currentSessionId.value) return
    await closeSession(currentSessionId.value)
    // Update local state
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    if (session) session.status = 'closed'
  }

  async function reopenCurrentSession() {
    if (!currentSessionId.value) return
    await reopenSession(currentSessionId.value)
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    if (session) session.status = 'active'
  }

  async function markCurrentAttention() {
    if (!currentSessionId.value) return
    await markAttention(currentSessionId.value)
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    if (session) session.status = 'needs_attention'
  }

  async function requestHumanHandoff() {
    if (!currentSessionId.value) return
    await requestHandoff(currentSessionId.value)
    const session = sessions.value.find((s) => s.id === currentSessionId.value)
    if (session) session.status = 'needs_attention'
  }

  return {
    sessions,
    currentSessionId,
    messages,
    loading,
    sending,
    currentSession,
    loadSessions,
    newSession,
    selectSession,
    postMessage,
    closeCurrentSession,
    reopenCurrentSession,
    markCurrentAttention,
    requestHumanHandoff,
  }
})
