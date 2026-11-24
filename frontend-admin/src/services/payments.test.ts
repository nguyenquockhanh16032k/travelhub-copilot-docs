import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AxiosResponse } from 'axios'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import { api } from './api'
import {
  createFinancialException,
  createPayment,
  listPayments,
  verifyPayment,
  verifyPaymentAsException,
} from './payments'
import type {
  AdminPayment,
  PaymentCreatePayload,
  PaymentExceptionCreatePayload,
} from '../types/payment'

const payment: AdminPayment = {
  id: 'payment-1',
  booking_id: 'booking-1',
  amount: '100.00',
  currency: 'VND',
  method: 'cash',
  status: 'pending',
  transaction_reference: null,
  notes: null,
  requires_resolution: false,
  resolution_reason: null,
  recorded_at: '2026-01-01T00:00:00Z',
  booking_reference: 'TH-1',
  booking_status: 'pending',
  booking_total: '100.00',
  verified_paid_amount: '0.00',
  outstanding_balance: '100.00',
  overpaid_amount: '0.00',
  payment_completion_status: 'UNPAID',
  recorded_by: 'admin@example.com',
  verified_by: null,
}

describe('payment service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lists filtered payments with backend pagination parameters', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: { items: [payment], total: 1, page: 1, size: 20, pages: 1 },
    } as AxiosResponse)

    await listPayments(1, 20, {
      search: ' TX-1 ',
      status: 'pending',
      method: 'cash',
    })

    expect(api.get).toHaveBeenCalledWith('/payments', {
      params: {
        page: 1,
        size: 20,
        search: 'TX-1',
        status_filter: 'pending',
        method_filter: 'cash',
        booking_id: undefined,
        requires_resolution: undefined,
      },
    })
  })

  it('sends an idempotency key with manual payment creation', async () => {
    const payload: PaymentCreatePayload = {
      booking_id: 'booking-1',
      amount: '100.00',
      currency: 'VND',
      method: 'cash',
      status: 'pending',
      transaction_reference: null,
      notes: null,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: payment,
    } as AxiosResponse<AdminPayment>)

    await createPayment(payload, 'request-key-1')

    expect(api.post).toHaveBeenCalledWith('/payments', payload, {
      headers: { 'Idempotency-Key': 'request-key-1' },
    })
  })

  it('uses explicit audited exception and verification endpoints', async () => {
    const exceptionPayload: PaymentExceptionCreatePayload = {
      booking_id: 'booking-1',
      amount: '110.00',
      currency: 'VND',
      method: 'cash',
      status: 'paid',
      transaction_reference: null,
      notes: null,
      reason: 'Late receipt',
      confirmation: true,
    }
    vi.mocked(api.post).mockResolvedValue({
      data: payment,
    } as AxiosResponse<AdminPayment>)

    await createFinancialException(exceptionPayload, 'exception-key')
    await verifyPayment('payment-1')
    await verifyPaymentAsException('payment-1', {
      reason: 'Late receipt',
      confirmation: true,
    })

    expect(api.post).toHaveBeenNthCalledWith(
      1,
      '/payments/exceptions',
      exceptionPayload,
      { headers: { 'Idempotency-Key': 'exception-key' } },
    )
    expect(api.post).toHaveBeenNthCalledWith(2, '/payments/payment-1/verify')
    expect(api.post).toHaveBeenNthCalledWith(
      3,
      '/payments/payment-1/financial-exception',
      { reason: 'Late receipt', confirmation: true },
    )
  })
})
