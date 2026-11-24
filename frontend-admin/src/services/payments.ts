import { api } from './api'
import type {
  AdminPaymentPage,
  PaymentCreatePayload,
  PaymentExceptionCreatePayload,
  PaymentExceptionVerifyPayload,
  PaymentRecord,
} from '../types/payment'

export interface PaymentFilters {
  search?: string
  status?: string
  method?: string
  bookingId?: string
  requiresResolution?: boolean
}

export async function listPayments(
  page: number,
  size: number,
  filters: PaymentFilters = {},
): Promise<AdminPaymentPage> {
  const response = await api.get<AdminPaymentPage>('/payments', {
    params: {
      page,
      size,
      search: filters.search?.trim() || undefined,
      status_filter: filters.status || undefined,
      method_filter: filters.method || undefined,
      booking_id: filters.bookingId || undefined,
      requires_resolution: filters.requiresResolution,
    },
  })
  return response.data
}

export async function createPayment(
  payload: PaymentCreatePayload,
  idempotencyKey: string,
): Promise<PaymentRecord> {
  const response = await api.post<PaymentRecord>(
    '/payments',
    payload,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return response.data
}

export async function createFinancialException(
  payload: PaymentExceptionCreatePayload,
  idempotencyKey: string,
): Promise<PaymentRecord> {
  const response = await api.post<PaymentRecord>(
    '/payments/exceptions',
    payload,
    { headers: { 'Idempotency-Key': idempotencyKey } },
  )
  return response.data
}

export async function verifyPayment(
  paymentId: string,
): Promise<PaymentRecord> {
  const response = await api.post<PaymentRecord>(
    `/payments/${paymentId}/verify`,
  )
  return response.data
}

export async function verifyPaymentAsException(
  paymentId: string,
  payload: PaymentExceptionVerifyPayload,
): Promise<PaymentRecord> {
  const response = await api.post<PaymentRecord>(
    `/payments/${paymentId}/financial-exception`,
    payload,
  )
  return response.data
}
