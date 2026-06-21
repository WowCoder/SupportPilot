import api from './index'

export function getRagLogs(params = {}) {
  return api.get('/api/rag-logs', { params })
}

export function getRagStats() {
  return api.get('/api/rag-logs/stats')
}

export function getRagLogDetail(logId) {
  return api.get(`/api/rag-logs/${logId}`)
}

export function triggerJudge(logId) {
  return api.post(`/api/rag-logs/${logId}/judge`)
}
