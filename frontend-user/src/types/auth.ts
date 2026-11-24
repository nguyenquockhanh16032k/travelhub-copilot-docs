export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface CurrentUser {
  id: string
  email: string
  is_active: boolean
  roles: string[]
}
