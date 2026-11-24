import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import { api } from './api'
import { fetchCurrentUser, login, logout } from './auth'

describe('customer authentication service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses the existing login endpoint', async () => {
    const tokens = {
      access_token: 'access',
      refresh_token: 'refresh',
      token_type: 'bearer',
    }
    vi.mocked(api.post).mockResolvedValue({ data: tokens })

    await expect(login('customer@example.com', 'password')).resolves.toEqual(
      tokens,
    )
    expect(api.post).toHaveBeenCalledWith('/auth/login', {
      email: 'customer@example.com',
      password: 'password',
    })
  })

  it('loads the authenticated identity and revokes refresh token on sign out', async () => {
    const user = {
      id: 'user-id',
      email: 'customer@example.com',
      is_active: true,
      roles: ['CUSTOMER'],
    }
    vi.mocked(api.get).mockResolvedValue({ data: user })
    vi.mocked(api.post).mockResolvedValue({ data: undefined })

    await expect(fetchCurrentUser()).resolves.toEqual(user)
    await expect(logout('refresh')).resolves.toBeUndefined()

    expect(api.get).toHaveBeenCalledWith('/auth/me')
    expect(api.post).toHaveBeenCalledWith('/auth/logout', {
      refresh_token: 'refresh',
    })
  })
})
