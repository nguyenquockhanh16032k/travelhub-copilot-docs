import { api } from './api'
import type {
  Departure,
  DepartureCreatePayload,
  DeparturePage,
  DepartureUpdatePayload,
  AdminDeparturePage,
} from '../types/catalog'

export async function listDepartures(
  page: number,
  size: number,
  tourId?: string,
  startDate?: string,
): Promise<DeparturePage> {
  return listAdminDepartures(page, size, tourId, startDate)
}

export async function listAdminDepartures(
  page: number,
  size: number,
  tourId?: string,
  startDate?: string,
): Promise<AdminDeparturePage> {
  const response = await api.get<AdminDeparturePage>('/admin/departures', {
    params: {
      page,
      size,
      tour_id: tourId || undefined,
      start_date: startDate || undefined,
    },
  })
  return response.data
}

export async function createDeparture(
  payload: DepartureCreatePayload,
): Promise<Departure> {
  const response = await api.post<Departure>('/departures', payload)
  return response.data
}

export async function updateDeparture(
  departureId: string,
  payload: DepartureUpdatePayload,
): Promise<Departure> {
  const response = await api.patch<Departure>(
    `/departures/${departureId}`,
    payload,
  )
  return response.data
}
