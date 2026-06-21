import api from './index'

export function login(username, password) {
  return api.post('/api/v1/auth/login', { username, password })
}

export function register(username, email, password) {
  return api.post('/api/v1/auth/register', { username, email, password })
}

export function refreshToken(refreshTokenStr) {
  return api.post('/api/v1/auth/refresh', { refresh_token: refreshTokenStr })
}

export function getMe() {
  return api.get('/api/v1/auth/me')
}
