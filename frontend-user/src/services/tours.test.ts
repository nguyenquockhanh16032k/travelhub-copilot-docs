import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AxiosResponse } from 'axios'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
  },
}))

import { api } from './api'
import { listTours } from './tours'
import type { TourPage } from '../types/tour'

describe('listTours', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('requests filtered tours with pagination and supports cancellation', async () => {
    const page: TourPage = {
      items: [],
      total: 0,
      page: 1,
      size: 12,
      pages: 0,
      currencies: [],
    }
    vi.mocked(api.get).mockResolvedValue({
      data: page,
    } as AxiosResponse<TourPage>)

    const signal = new AbortController().signal
    await expect(
      listTours(
        1,
        12,
        { keyword: ' beach ', destination: ' Da Lat ', currency: 'VND' },
        signal,
      ),
    ).resolves.toEqual(page)

    expect(api.get).toHaveBeenCalledWith('/tours', {
      params: {
        page: 1,
        size: 12,
        keyword: 'beach',
        destination: 'Da Lat',
        min_price: undefined,
        max_price: undefined,
        departure_from: undefined,
        departure_to: undefined,
        min_duration: undefined,
        max_duration: undefined,
        traveler_count: undefined,
        available_only: undefined,
        currency: 'VND',
        sort: undefined,
      },
      signal,
    })
  })

  it('omits blank and unset search filters', async () => {
    const page: TourPage = {
      items: [],
      total: 0,
      page: 1,
      size: 12,
      pages: 0,
      currencies: [],
    }
    vi.mocked(api.get).mockResolvedValue({
      data: page,
    } as AxiosResponse<TourPage>)

    await listTours(1, 12, { destination: '  ' })

    expect(api.get).toHaveBeenCalledWith('/tours', {
      params: {
        page: 1,
        size: 12,
        keyword: undefined,
        destination: undefined,
        min_price: undefined,
        max_price: undefined,
        departure_from: undefined,
        departure_to: undefined,
        min_duration: undefined,
        max_duration: undefined,
        traveler_count: undefined,
        available_only: undefined,
        currency: undefined,
        sort: undefined,
      },
      signal: undefined,
    })
  })
})
