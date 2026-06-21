import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // --- State ---
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || null)

  // --- Getters ---
  const isLoggedIn = computed(() => !!accessToken.value && !!user.value)
  const isTechSupport = computed(() => user.value?.role === 'tech_support')
  const currentUser = computed(() => user.value)

  // --- Actions ---
  function setTokens(access, refresh) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function setUser(userData) {
    user.value = userData
    localStorage.setItem('user', JSON.stringify(userData))
  }

  async function login(username, password) {
    const { data } = await loginApi(username, password)
    setTokens(data.data.access_token, data.data.refresh_token)
    setUser(data.data.user)
    return data.data.user
  }

  async function register(username, email, password) {
    const { data } = await registerApi(username, email, password)
    setTokens(data.data.access_token, data.data.refresh_token)
    setUser(data.data.user)
    return data.data.user
  }

  async function fetchUser() {
    try {
      const { data } = await getMe()
      setUser(data.data)
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('user')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return {
    user,
    accessToken,
    refreshToken,
    isLoggedIn,
    isTechSupport,
    currentUser,
    login,
    register,
    fetchUser,
    logout,
    setTokens,
  }
})
