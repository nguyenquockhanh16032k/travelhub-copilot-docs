import { api } from './api'
import type {
  AssignableRoleOption,
  ManagedUser,
  ManagedUserPage,
  UserCreatePayload,
  UserUpdatePayload,
} from '../types/user'

export async function listUsers(
  page: number,
  size: number,
  search?: string,
): Promise<ManagedUserPage> {
  const response = await api.get<ManagedUserPage>('/users', {
    params: { page, size, search: search || undefined },
  })
  return response.data
}

export async function listAssignableRoles(): Promise<AssignableRoleOption[]> {
  const response = await api.get<AssignableRoleOption[]>('/users/roles')
  return response.data
}

export async function createUser(
  payload: UserCreatePayload,
): Promise<ManagedUser> {
  const response = await api.post<ManagedUser>('/users', payload)
  return response.data
}

export async function updateUser(
  userId: string,
  payload: UserUpdatePayload,
): Promise<ManagedUser> {
  const response = await api.patch<ManagedUser>(`/users/${userId}`, payload)
  return response.data
}
