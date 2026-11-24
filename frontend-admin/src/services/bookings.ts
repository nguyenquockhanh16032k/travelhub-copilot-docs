import { api } from './api'
import type {
  Booking,
  BookingCreatePayload,
  BookingPage,
  BookingStatus,
  BookingUpdatePayload,
} from '../types/booking'

export async function createBooking(
  payload: BookingCreatePayload,
): Promise<Booking> {
  const response = await api.post<Booking>('/bookings', payload)
  return response.data
}

export async function listBookings(
  page: number,
  size: number,
  status?: BookingStatus,
  search?: string,
): Promise<BookingPage> {
  const response = await api.get<BookingPage>('/bookings', {
    params: {
      page,
      size,
      status_filter: status,
      search: search?.trim() || undefined,
    },
  })
  return response.data
}

export async function getBooking(bookingId: string): Promise<Booking> {
  const response = await api.get<Booking>(`/bookings/${bookingId}`)
  return response.data
}

export async function updateBooking(
  bookingId: string,
  payload: BookingUpdatePayload,
): Promise<Booking> {
  const response = await api.patch<Booking>(`/bookings/${bookingId}`, payload)
  return response.data
}

export async function changeBookingStatus(
  bookingId: string,
  status: 'confirmed' | 'cancelled',
  reason: string,
): Promise<Booking> {
  const response = await api.post<Booking>(
    `/bookings/${bookingId}/${status === 'confirmed' ? 'confirm' : 'cancel'}`,
    { reason: reason.trim() || null },
  )
  return response.data
}
