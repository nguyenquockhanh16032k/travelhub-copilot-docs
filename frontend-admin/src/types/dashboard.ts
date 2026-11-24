export interface UpcomingDepartureSummary {
  id: string
  tour_title: string
  start_date: string
  end_date: string
  available_seats: number
  price?: string
  currency?: string
}

export interface PaymentCurrencySummary {
  currency: string
  paid_amount: string
  pending_amount: string
}

export interface DashboardSummary {
  booking_count: number
  pending_booking_count: number
  upcoming_departures: UpcomingDepartureSummary[]
  payments_by_currency?: PaymentCurrencySummary[]
}
