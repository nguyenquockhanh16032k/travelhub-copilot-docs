import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AxiosResponse } from 'axios'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

import { api } from './api'
import { updateTour } from './tours'
import type { Tour, TourUpdatePayload } from '../types/catalog'

describe('updateTour', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('updates a tour using the existing admin API contract', async () => {
    const tour: Tour = {
      id: 'tour-1',
      title: 'Updated tour',
      slug: 'updated-tour',
      description: null,
      duration_days: 3,
      destination: 'Da Lat',
      status: 'published',
    }
    const payload: TourUpdatePayload = {
      title: tour.title,
      slug: tour.slug,
      description: tour.description,
      duration_days: tour.duration_days,
      destination: tour.destination,
      status: tour.status,
    }
    vi.mocked(api.patch).mockResolvedValue({
      data: tour,
    } as AxiosResponse<Tour>)

    await expect(updateTour(tour.id, payload)).resolves.toEqual(tour)

    expect(api.patch).toHaveBeenCalledWith('/tours/tour-1', payload)
  })
})
