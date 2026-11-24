import { api } from './api'
import type { Guide, GuidePage, GuidePayload } from '../types/operations'

export async function listGuides(
  page: number,
  size: number,
  search?: string,
): Promise<GuidePage> {
  const response = await api.get<GuidePage>('/guides', {
    params: { page, size, search: search || undefined },
  })
  return response.data
}

export async function createGuide(payload: GuidePayload): Promise<Guide> {
  const response = await api.post<Guide>('/guides', payload)
  return response.data
}

export async function updateGuide(
  guideId: string,
  payload: GuidePayload,
): Promise<Guide> {
  const response = await api.patch<Guide>(`/guides/${guideId}`, payload)
  return response.data
}
