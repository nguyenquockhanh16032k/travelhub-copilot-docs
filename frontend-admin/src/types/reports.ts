export interface ExpenseReportRow {
  departure_id: string
  tour_title: string
  departure_start_date: string
  category: string
  currency: string
  status: string
  total_amount: string
  expense_count: number
}

export interface ExpenseReportPage {
  items: ExpenseReportRow[]
  total: number
  page: number
  size: number
  pages: number
}
