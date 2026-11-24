import type { BookingStatus } from './booking'

export type PaymentStatus = 'pending' | 'paid' | 'failed' | 'refunded'
export type PaymentMethod = 'cash' | 'bank_transfer' | 'card' | 'other'
export type PaymentCompletionStatus =
  | 'UNPAID'
  | 'PARTIALLY_PAID'
  | 'FULLY_PAID'
  | 'OVERPAID'

export interface PaymentRecord {
  id: string
  booking_id: string
  amount: string
  currency: string
  method: PaymentMethod
  status: PaymentStatus
  transaction_reference: string | null
  notes: string | null
  requires_resolution: boolean
  resolution_reason: string | null
  recorded_at: string
}

export interface AdminPayment extends PaymentRecord {
  booking_reference: string
  booking_status: BookingStatus
  booking_total: string
  verified_paid_amount: string
  outstanding_balance: string
  overpaid_amount: string
  payment_completion_status: PaymentCompletionStatus
  recorded_by: string | null
  verified_by: string | null
}

export interface PaymentBookingSummary {
  booking_id: string
  booking_reference: string
  booking_status: BookingStatus
  booking_total: string
  currency: string
  verified_paid_amount: string
  outstanding_balance: string
  overpaid_amount: string
  payment_completion_status: PaymentCompletionStatus
}

export interface AdminPaymentPage {
  items: AdminPayment[]
  total: number
  page: number
  size: number
  pages: number
  booking_summary: PaymentBookingSummary | null
}

export interface PaymentCreatePayload {
  booking_id: string
  amount: string
  currency: string
  method: PaymentMethod
  status: 'pending'
  transaction_reference: string | null
  notes: string | null
}

export interface PaymentExceptionCreatePayload
  extends Omit<PaymentCreatePayload, 'status'> {
  status: 'paid'
  reason: string
  confirmation: true
}

export interface PaymentExceptionVerifyPayload {
  reason: string
  confirmation: true
}
