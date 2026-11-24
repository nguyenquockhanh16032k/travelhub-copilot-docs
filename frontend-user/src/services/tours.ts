import { api } from './api'
import type {
  TourDetail,
  TourPage,
  TourSearchFilters,
} from '../types/tour'

export async function listTours(
  page: number,
  size: number,
  filters: TourSearchFilters = {},
  signal?: AbortSignal,
): Promise<TourPage> {
  const response = await api.get<TourPage>('/tours', {
    params: {
      page,
      size,
      keyword: filters.keyword?.trim() || undefined,
      destination: filters.destination?.trim() || undefined,
      min_price: filters.min_price || undefined,
      max_price: filters.max_price || undefined,
      departure_from: filters.departure_from || undefined,
      departure_to: filters.departure_to || undefined,
      min_duration: filters.min_duration || undefined,
      max_duration: filters.max_duration || undefined,
      traveler_count: filters.traveler_count || undefined,
      available_only: filters.available_only || undefined,
      currency: filters.currency || undefined,
      sort: filters.sort || undefined,
    },
    signal,
  })
  return response.data
}

export async function getTour(tourId: string): Promise<TourDetail> {
  const response = await api.get<TourDetail>(`/tours/${tourId}`)
  return response.data
}
