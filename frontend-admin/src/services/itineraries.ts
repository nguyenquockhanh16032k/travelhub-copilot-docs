import { api } from './api'
import type { ItineraryItem, ItineraryPayload } from '../types/itinerary'

export async function listItineraries(
  tourId: string,
): Promise<ItineraryItem[]> {
  const response = await api.get<ItineraryItem[]>(
    `/tours/${tourId}/itineraries`,
  )
  return response.data
}

export async function createItineraryItem(
  tourId: string,
  payload: ItineraryPayload,
): Promise<ItineraryItem> {
  const response = await api.post<ItineraryItem>(
    `/tours/${tourId}/itineraries`,
    payload,
  )
  return response.data
}

export async function updateItineraryItem(
  tourId: string,
  itineraryId: string,
  payload: Partial<ItineraryPayload>,
): Promise<ItineraryItem> {
  const response = await api.patch<ItineraryItem>(
    `/tours/${tourId}/itineraries/${itineraryId}`,
    payload,
  )
  return response.data
}

export async function deleteItineraryItem(
  tourId: string,
  itineraryId: string,
): Promise<void> {
  await api.delete(`/tours/${tourId}/itineraries/${itineraryId}`)
}
