export interface Guide {
  id: string
  user_id: string | null
  full_name: string
  email: string | null
  phone: string | null
}

export interface GuidePage {
  items: Guide[]
  total: number
  page: number
  size: number
  pages: number
}

export interface GuidePayload {
  full_name: string
  email: string | null
  phone: string | null
  user_id: string | null
}

export interface TourAssignment {
  id: string
  departure_id: string
  guide_id: string
  role: string
  status: string
  guide: Guide
}

export interface TourAssignmentPage {
  items: TourAssignment[]
  total: number
  page: number
  size: number
  pages: number
}

export interface TourAssignmentPayload {
  guide_id: string
  role: string
  status: string
}

export interface Supplier {
  id: string
  name: string
  service_category: string
}

export interface SupplierPage {
  items: Supplier[]
  total: number
  page: number
  size: number
  pages: number
}

export interface SupplierPayload {
  name: string
  service_category: string
}

export interface TourExpense {
  id: string
  departure_id: string
  supplier_id: string | null
  category: string
  amount: string
  currency: string
  status: string
  note: string | null
  supplier: Supplier | null
}

export interface TourExpensePage {
  items: TourExpense[]
  total: number
  page: number
  size: number
  pages: number
}

export interface TourExpensePayload {
  supplier_id: string | null
  category: string
  amount: string
  currency: string
  status: string
  note: string | null
}
