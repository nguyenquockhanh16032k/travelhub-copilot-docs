import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AxiosResponse } from 'axios'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

import { api } from './api'
import { createUser, listAssignableRoles, updateUser } from './users'
import type {
  AssignableRoleOption,
  ManagedUser,
  UserCreatePayload,
  UserUpdatePayload,
} from '../types/user'

describe('user management API service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads roles scoped to the current administrator', async () => {
    const roles: AssignableRoleOption[] = [
      { code: 'STAFF', description: 'Operational access' },
    ]
    vi.mocked(api.get).mockResolvedValue({
      data: roles,
    } as AxiosResponse<AssignableRoleOption[]>)

    await expect(listAssignableRoles()).resolves.toEqual(roles)
    expect(api.get).toHaveBeenCalledWith('/users/roles')
  })

  it('creates and updates users through protected endpoints', async () => {
    const user: ManagedUser = {
      id: 'user-1',
      email: 'staff@example.com',
      is_active: true,
      roles: ['STAFF'],
      created_at: '2026-11-23T00:00:00Z',
    }
    const createPayload: UserCreatePayload = {
      email: user.email,
      password: 'secure-password',
      role: 'STAFF',
    }
    const updatePayload: UserUpdatePayload = {
      is_active: false,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: user,
    } as AxiosResponse<ManagedUser>)
    vi.mocked(api.patch).mockResolvedValue({
      data: { ...user, is_active: false },
    } as AxiosResponse<ManagedUser>)

    await expect(createUser(createPayload)).resolves.toEqual(user)
    await expect(updateUser(user.id, updatePayload)).resolves.toMatchObject({
      is_active: false,
    })

    expect(api.post).toHaveBeenCalledWith('/users', createPayload)
    expect(api.patch).toHaveBeenCalledWith('/users/user-1', updatePayload)
  })
})
