import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosHeaders, type AxiosResponse } from 'axios'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import { api } from './api'
import { createBooking } from './bookings'
import type {
  BookingCreatePayload,
  BookingResponse,
  CustomerBooking,
  CustomerBookingPage,
} from '../types/booking'
import { getMyBooking, listMyBookings } from './bookings'

function response<T>(data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { headers: new AxiosHeaders() },
  }
}

describe('createBooking', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('submits the guest booking request to the public bookings endpoint', async () => {
    const payload: BookingCreatePayload = {
      departure_id: 'departure-id',
      contact_name: 'Guest',
      contact_email: 'guest@example.com',
      contact_phone: '0900000000',
      travelers: [{ full_name: 'Guest One', traveler_type: 'adult' }],
      notes: null,
    }
    const booking = {
      id: 'booking-id',
      reference: 'TH-123456789ABC',
      departure_id: payload.departure_id,
      customer_id: null,
      contact_name: payload.contact_name,
      contact_email: payload.contact_email,
      contact_phone: payload.contact_phone,
      passenger_count: 1,
      status: 'pending',
      total_amount: '100.00',
      currency: 'VND',
      notes: null,
      travelers: [],
      status_history: [],
    } satisfies BookingResponse
    const response: AxiosResponse<BookingResponse> = {
      data: booking,
      status: 201,
      statusText: 'Created',
      headers: {},
      config: {
        headers: new AxiosHeaders(),
      },
    }
    vi.mocked(api.post).mockResolvedValue(response)

    await expect(createBooking(payload)).resolves.toEqual(booking)

    expect(api.post).toHaveBeenCalledWith('/bookings', payload)
  })

  it('loads the authenticated customer booking collection', async () => {
    const page: CustomerBookingPage = {
      items: [],
      total: 0,
      page: 1,
      size: 20,
      pages: 0,
    }
    vi.mocked(api.get).mockResolvedValue(response(page))

    await expect(listMyBookings(1, 20)).resolves.toEqual(page)

    expect(api.get).toHaveBeenCalledWith('/customers/me/bookings', {
      params: { page: 1, size: 20 },
    })
  })

  it('loads one customer booking by its identifier', async () => {
    const booking = {
      id: 'booking-id',
      reference: 'TH-123456789ABC',
      status: 'confirmed',
      passenger_count: 1,
      total_amount: '100.00',
      currency: 'VND',
      verified_paid_amount: '25.00',
      outstanding_balance: '75.00',
      payment_completion_status: 'PARTIALLY_PAID',
      expires_at: null,
      tour_title: 'Da Lat',
      destination: 'Da Lat',
      duration_days: 2,
      departure_start_date: '2026-12-01',
      departure_end_date: '2026-12-03',
      departure_status: 'open',
      travelers: [],
      status_history: [],
      payments: [],
    } satisfies CustomerBooking
    vi.mocked(api.get).mockResolvedValue(response(booking))

    await expect(getMyBooking(booking.id)).resolves.toEqual(booking)

    expect(api.get).toHaveBeenCalledWith(
      `/customers/me/bookings/${booking.id}`,
    )
  })
})
