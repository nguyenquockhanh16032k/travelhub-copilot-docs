import { api } from './api'
import type { CurrentUser, TokenResponse } from '../types/auth'

export async function login(email: string, password: string): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>('/auth/login', {
    email,
    password,
  })
  return response.data
}

export async function fetchCurrentUser(): Promise<CurrentUser> {
  const response = await api.get<CurrentUser>('/auth/me')
  return response.data
}

export async function logout(refreshToken: string): Promise<void> {
  await api.post('/auth/logout', { refresh_token: refreshToken })
}
