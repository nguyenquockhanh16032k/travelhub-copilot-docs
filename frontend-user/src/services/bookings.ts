import { api } from './api'
import type {
  BookingCreatePayload,
  BookingResponse,
  CustomerBooking,
  CustomerBookingPage,
} from '../types/booking'

export async function createBooking(
  payload: BookingCreatePayload,
): Promise<BookingResponse> {
  const response = await api.post<BookingResponse>('/bookings', payload)
  return response.data
}

export async function listMyBookings(
  page: number,
  size: number,
): Promise<CustomerBookingPage> {
  const response = await api.get<CustomerBookingPage>('/customers/me/bookings', {
    params: { page, size },
  })
  return response.data
}

export async function getMyBooking(
  bookingId: string,
): Promise<CustomerBooking> {
  const response = await api.get<CustomerBooking>(
    `/customers/me/bookings/${bookingId}`,
  )
  return response.data
}
