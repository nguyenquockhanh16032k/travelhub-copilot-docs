export type BookingStatus =
  | 'pending'
  | 'confirmed'
  | 'cancelled'
  | 'expired'
  | 'rejected'
  | 'completed'

export interface BookingTraveler {
  id: string
  full_name: string
  traveler_type: string
}

export interface BookingStatusHistoryEntry {
  id: string
  old_status: BookingStatus | null
  new_status: BookingStatus
  actor_user_id: string | null
  reason: string | null
  changed_at: string
}

export interface Booking {
  id: string
  reference: string
  departure_id: string
  customer_id: string | null
  contact_name: string
  contact_email: string
  contact_phone: string
  passenger_count: number
  status: BookingStatus
  total_amount?: string
  currency?: string
  notes: string | null
  travelers: BookingTraveler[]
  status_history: BookingStatusHistoryEntry[]
}

export interface BookingPage {
  items: Booking[]
  total: number
  page: number
  size: number
  pages: number
}

export interface BookingTravelerInput {
  full_name: string
  traveler_type: string
}

export interface BookingCreatePayload {
  departure_id: string
  customer_id: string
  contact_name: string
  contact_email: string
  contact_phone: string
  travelers: BookingTravelerInput[]
  notes: string | null
}

export interface BookingUpdatePayload {
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  travelers?: BookingTravelerInput[]
}
