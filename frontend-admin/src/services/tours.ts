import { api } from './api'
import type {
  Tour,
  TourCreatePayload,
  TourPage,
  TourUpdatePayload,
} from '../types/catalog'

export async function listTours(
  page: number,
  size: number,
  destination?: string,
  sort = '-created_at',
): Promise<TourPage> {
  const response = await api.get<TourPage>('/admin/tours', {
    params: { page, size, destination: destination || undefined, sort },
  })
  return response.data
}

export async function createTour(payload: TourCreatePayload): Promise<Tour> {
  const response = await api.post<Tour>('/tours', payload)
  return response.data
}

export async function updateTour(
  tourId: string,
  payload: TourUpdatePayload,
): Promise<Tour> {
  const response = await api.patch<Tour>(`/tours/${tourId}`, payload)
  return response.data
}
