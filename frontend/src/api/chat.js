import api from './index'

export function listSessions() {
  return api.get('/api/v1/chat/sessions')
}

export function createSession() {
  return api.post('/api/v1/chat/sessions')
}

export function getSession(sessionId) {
  return api.get(`/api/v1/chat/sessions/${sessionId}`)
}

export function listMessages(sessionId, page = 1, pageSize = 50) {
  return api.get(`/api/v1/chat/sessions/${sessionId}/messages`, {
    params: { page, page_size: pageSize },
  })
}

export function sendMessage(sessionId, content) {
  return api.post(`/api/v1/chat/sessions/${sessionId}/messages`, { content })
}

export function closeSession(sessionId) {
  return api.post(`/api/v1/chat/sessions/${sessionId}/close`)
}

export function reopenSession(sessionId) {
  return api.post(`/api/v1/chat/sessions/${sessionId}/reopen`)
}

export function markAttention(sessionId) {
  return api.post(`/api/v1/chat/sessions/${sessionId}/mark-attention`)
}

export function requestHandoff(sessionId) {
  return api.post(`/api/ticket/${sessionId}/handoff`)
}

export function getStats() {
  return api.get('/api/v1/chat/stats')
}
