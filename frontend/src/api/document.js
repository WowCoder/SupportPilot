import api from './index'

export function listDocuments(params = {}) {
  return api.get('/api/v1/documents', { params })
}

export function uploadDocument(formData) {
  return api.post('/api/v1/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteDocument(id) {
  return api.delete(`/api/v1/documents/${id}`)
}

export function getDocStats() {
  return api.get('/api/v1/documents/stats')
}
