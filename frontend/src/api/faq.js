import api from './index'

export function listEntries(params = {}) {
  return api.get('/api/v1/faq/entries', { params })
}

export function createEntry(data) {
  return api.post('/api/v1/faq/entries', data)
}

export function updateEntry(id, data) {
  return api.put(`/api/v1/faq/entries/${id}`, data)
}

export function deleteEntry(id) {
  return api.delete(`/api/v1/faq/entries/${id}`)
}

export function bulkDelete(ids) {
  return api.post('/api/v1/faq/entries/bulk-delete', { ids })
}

export function listCategories() {
  return api.get('/api/v1/faq/categories')
}

export function testSearch(query, k = 5, threshold = 0.25) {
  return api.post('/api/faq/test-search', { query, k, similarity_threshold: threshold })
}
