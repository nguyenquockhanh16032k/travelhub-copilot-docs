import axios, {
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { AuthTokens } from '../types/auth'

const baseURL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL,
  timeout: 15000,
})

const ACCESS_TOKEN_KEY = 'travelhub_access_token'
const REFRESH_TOKEN_KEY = 'travelhub_refresh_token'

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise

  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) throw new Error('No refresh token')

  refreshPromise = axios
    .post<AuthTokens>(`${baseURL}/auth/refresh`, {
      refresh_token: refreshToken,
    })
    .then((response) => {
      const tokens = response.data
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
      return tokens.access_token
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (
    error: AxiosError & {
      config?: InternalAxiosRequestConfig & { _retry?: boolean }
    },
  ) => {
    const originalRequest = error.config
    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry
    ) {
      return Promise.reject(error)
    }

    originalRequest._retry = true
    try {
      const accessToken = await refreshAccessToken()
      originalRequest.headers.set('Authorization', `Bearer ${accessToken}`)
      return api(originalRequest)
    } catch {
      localStorage.removeItem(ACCESS_TOKEN_KEY)
      localStorage.removeItem(REFRESH_TOKEN_KEY)
      window.dispatchEvent(new CustomEvent('travelhub-session-expired'))
      return Promise.reject(error)
    }
  },
)

export function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function hasStoredSession(): boolean {
  return Boolean(localStorage.getItem(ACCESS_TOKEN_KEY))
    || Boolean(localStorage.getItem(REFRESH_TOKEN_KEY))
}
