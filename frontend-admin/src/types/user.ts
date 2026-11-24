export type AssignableRole = 'ADMIN' | 'STAFF' | 'CUSTOMER'
export type UserRole = 'SUPER_ADMIN' | AssignableRole

export interface ManagedUser {
  id: string
  email: string
  is_active: boolean
  roles: UserRole[]
  created_at: string
}

export interface ManagedUserPage {
  items: ManagedUser[]
  total: number
  page: number
  size: number
  pages: number
}

export interface AssignableRoleOption {
  code: AssignableRole
  description: string
}

export interface UserCreatePayload {
  email: string
  password: string
  role: AssignableRole
}

export interface UserUpdatePayload {
  email?: string
  password?: string
  role?: UserRole
  is_active?: boolean
}
