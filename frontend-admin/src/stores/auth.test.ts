import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const storage = new Map<string, string>()

beforeAll(() => {
  vi.stubGlobal('localStorage', {
    clear: vi.fn(() => storage.clear()),
    getItem: vi.fn((key: string) => storage.get(key) ?? null),
    key: vi.fn((index: number) => Array.from(storage.keys())[index] ?? null),
    removeItem: vi.fn((key: string) => storage.delete(key)),
    setItem: vi.fn((key: string, value: string) => storage.set(key, value)),
    get length() {
      return storage.size
    },
  })
})

afterAll(() => {
  vi.unstubAllGlobals()
})

vi.mock('../services/api', () => ({
  clearStoredTokens: vi.fn(() => localStorage.clear()),
  setStoredTokens: vi.fn((accessToken: string, refreshToken: string) => {
    localStorage.setItem('travelhub_access_token', accessToken)
    localStorage.setItem('travelhub_refresh_token', refreshToken)
  }),
}))

vi.mock('../services/auth', () => ({
  login: vi.fn(),
  fetchCurrentUser: vi.fn(),
  logout: vi.fn(),
}))

import { useAuthStore } from './auth'
import { fetchCurrentUser, login, logout } from '../services/auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('stores the session after login', async () => {
    vi.mocked(login).mockResolvedValue({
      access_token: 'access',
      refresh_token: 'refresh',
      token_type: 'bearer',
    })
    vi.mocked(fetchCurrentUser).mockResolvedValue({
      id: '00000000-0000-0000-0000-000000000001',
      email: 'admin@travelhub.local',
      is_active: true,
      roles: ['ADMIN'],
    })

    const auth = useAuthStore()
    await auth.signIn('admin@travelhub.local', 'secure-password')

    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.email).toBe('admin@travelhub.local')
    expect(localStorage.getItem('travelhub_refresh_token')).toBe('refresh')
  })

  it('clears the session on logout', async () => {
    localStorage.setItem('travelhub_refresh_token', 'refresh')
    vi.mocked(logout).mockResolvedValue()

    const auth = useAuthStore()
    auth.user = {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'admin@travelhub.local',
      is_active: true,
      roles: ['ADMIN'],
    }
    await auth.signOut()

    expect(auth.isAuthenticated).toBe(false)
    expect(localStorage.getItem('travelhub_refresh_token')).toBeNull()
  })
})
