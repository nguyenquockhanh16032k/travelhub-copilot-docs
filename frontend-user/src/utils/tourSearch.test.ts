import { describe, expect, it } from 'vitest'

import {
  emptyTourSearch,
  parseTourSearch,
  tourSearchFilterCount,
  tourSearchQuery,
  validateTourSearch,
} from './tourSearch'

describe('tour search URL state', () => {
  it('restores filters, sorting, currency and pagination from a shared URL', () => {
    expect(
      parseTourSearch({
        keyword: 'beach',
        destination: 'Da Lat',
        min_price: '100',
        currency: 'vnd',
        departure_from: '2026-09-01',
        traveler_count: '2',
        available_only: 'true',
        sort: 'price_asc',
        page: '3',
      }),
    ).toEqual({
      ...emptyTourSearch(),
      keyword: 'beach',
      destination: 'Da Lat',
      min_price: '100',
      currency: 'VND',
      departure_from: '2026-09-01',
      traveler_count: '2',
      available_only: true,
      sort: 'price_asc',
      page: 3,
    })
  })

  it('serializes the search state without defaults and can clear all filters', () => {
    const state = {
      ...emptyTourSearch(),
      destination: ' Da Lat ',
      currency: 'VND',
      available_only: true,
      sort: 'earliest_departure' as const,
      page: 2,
    }

    expect(tourSearchQuery(state)).toEqual({
      destination: 'Da Lat',
      currency: 'VND',
      available_only: 'true',
      sort: 'earliest_departure',
      page: '2',
    })
    expect(tourSearchQuery(emptyTourSearch())).toEqual({})
  })

  it('counts active filter values for the filter indicators', () => {
    expect(
      tourSearchFilterCount({
        ...emptyTourSearch(),
        keyword: 'coast',
        currency: 'VND',
        available_only: true,
      }),
    ).toBe(3)
    expect(
      tourSearchFilterCount({
        ...emptyTourSearch(),
        sort: 'earliest_departure',
      }),
    ).toBe(1)
  })

  it('validates related price, date and traveler ranges before searching', () => {
    expect(
      validateTourSearch({
        ...emptyTourSearch(),
        min_price: '200',
        max_price: '100',
      }),
    ).toBe('Choose a currency before setting a price range.')
    expect(
      validateTourSearch({
        ...emptyTourSearch(),
        currency: 'VND',
        min_price: '200',
        max_price: '100',
      }),
    ).toBe('Minimum price must not exceed maximum price.')
    expect(
      validateTourSearch({
        ...emptyTourSearch(),
        min_duration: '3',
        max_duration: '2',
      }),
    ).toBe('Minimum duration must not exceed maximum duration.')
  })
})
