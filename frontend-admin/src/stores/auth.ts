import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { clearStoredTokens, setStoredTokens } from '../services/api'
import { fetchCurrentUser, login, logout } from '../services/auth'
import type { CurrentUser } from '../types/auth'

const REFRESH_TOKEN_KEY = 'travelhub_refresh_token'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const loading = ref(false)
  const error = ref('')

  const isAuthenticated = computed(() => user.value !== null)

  async function signIn(email: string, password: string): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const tokens = await login(email, password)
      setStoredTokens(tokens.access_token, tokens.refresh_token)
      user.value = await fetchCurrentUser()
    } catch (err) {
      clearStoredTokens()
      error.value =
        err instanceof Error ? err.message : 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function restoreSession(): Promise<void> {
    if (!localStorage.getItem(REFRESH_TOKEN_KEY)) {
      user.value = null
      return
    }
    try {
      user.value = await fetchCurrentUser()
    } catch {
      clearStoredTokens()
      user.value = null
    }
  }

  async function signOut(): Promise<void> {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    try {
      if (refreshToken) {
        await logout(refreshToken)
      }
    } finally {
      clearStoredTokens()
      user.value = null
    }
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    signIn,
    restoreSession,
    signOut,
  }
})
