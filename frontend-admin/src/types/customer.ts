export interface Customer {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  address: string | null
  user_id: string | null
}

export interface CustomerPage {
  items: Customer[]
  total: number
  page: number
  size: number
  pages: number
}

export interface CustomerAccountOption {
  id: string
  email: string
}

export interface CustomerAccountPage {
  items: CustomerAccountOption[]
  total: number
  page: number
  size: number
  pages: number
}

export interface CustomerPayload {
  full_name: string
  email: string | null
  phone: string | null
  address: string | null
  user_id?: string | null
}
