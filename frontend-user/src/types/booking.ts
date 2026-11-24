export type BookingStatus =
  | 'pending'
  | 'confirmed'
  | 'cancelled'
  | 'expired'
  | 'rejected'
  | 'completed'

export interface TravelerInput {
  full_name: string
  traveler_type: string
}

export interface BookingCreatePayload {
  departure_id: string
  contact_name: string
  contact_email: string
  contact_phone: string
  travelers: TravelerInput[]
  notes: string | null
}

export interface BookingResponse {
  id: string
  reference: string
  departure_id: string
  customer_id: string | null
  contact_name: string
  contact_email: string
  contact_phone: string
  passenger_count: number
  status: BookingStatus
  total_amount: string
  currency: string
  notes: string | null
  travelers: Array<{
    id: string
    full_name: string
    traveler_type: string
  }>
  status_history: Array<{
    id: string
    old_status: BookingStatus | null
    new_status: BookingStatus
    actor_user_id: string | null
    reason: string | null
    changed_at: string
  }>
}

export interface BookingConfirmation {
  reference: string
  status: BookingStatus
  total_amount: string
  currency: string
}

export interface CustomerBooking {
  id: string
  reference: string
  status: BookingStatus
  passenger_count: number
  total_amount: string
  currency: string
  verified_paid_amount: string
  outstanding_balance: string
  payment_completion_status:
    | 'UNPAID'
    | 'PARTIALLY_PAID'
    | 'FULLY_PAID'
    | 'OVERPAID'
  expires_at: string | null
  tour_title: string
  destination: string
  duration_days: number
  departure_start_date: string
  departure_end_date: string
  departure_status: string
  travelers: Array<{
    id: string
    full_name: string
    traveler_type: string
  }>
  status_history: Array<{
    old_status: BookingStatus | null
    new_status: BookingStatus
    changed_at: string
  }>
  payments: Array<{
    id: string
    amount: string
    currency: string
    method: 'cash' | 'bank_transfer' | 'card' | 'other'
    status: 'pending' | 'paid' | 'failed' | 'refunded'
    transaction_reference: string | null
    recorded_at: string
  }>
}

export interface CustomerBookingPage {
  items: CustomerBooking[]
  total: number
  page: number
  size: number
  pages: number
}
