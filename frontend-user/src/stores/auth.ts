import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { clearTokens, hasStoredSession, storeTokens } from '../services/api'
import { fetchCurrentUser, login, logout } from '../services/auth'
import type { CurrentUser } from '../types/auth'

const REFRESH_TOKEN_KEY = 'travelhub_refresh_token'

export const useAuthStore = defineStore('customer-auth', () => {
  const user = ref<CurrentUser | null>(null)
  const loading = ref(false)
  const error = ref('')
  const isAuthenticated = computed(() => user.value !== null)

  window.addEventListener('travelhub-session-expired', () => {
    user.value = null
  })

  async function signIn(email: string, password: string): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const tokens = await login(email, password)
      storeTokens(tokens.access_token, tokens.refresh_token)
      const currentUser = await fetchCurrentUser()
      if (!currentUser.roles.includes('CUSTOMER')) {
        clearTokens()
        throw new Error('This account does not have customer access.')
      }
      user.value = currentUser
    } catch (caught) {
      clearTokens()
      error.value =
        caught instanceof Error ? caught.message : 'Unable to sign in.'
      throw caught
    } finally {
      loading.value = false
    }
  }

  async function restoreSession(): Promise<void> {
    if (!hasStoredSession()) return
    try {
      const currentUser = await fetchCurrentUser()
      if (!currentUser.roles.includes('CUSTOMER')) {
        clearTokens()
        user.value = null
        return
      }
      user.value = currentUser
    } catch {
      clearTokens()
      user.value = null
    }
  }

  async function signOut(): Promise<void> {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    try {
      if (refreshToken) await logout(refreshToken)
    } finally {
      clearTokens()
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
