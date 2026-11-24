import type { LocationQuery, LocationQueryRaw } from 'vue-router'
import type { TourSearchFilters } from '../types/tour'

export type TourSort =
  | 'recently_added'
  | 'earliest_departure'
  | 'price_asc'
  | 'price_desc'

export interface TourSearchState extends TourSearchFilters {
  keyword: string
  destination: string
  min_price: string
  max_price: string
  departure_from: string
  departure_to: string
  min_duration: string
  max_duration: string
  traveler_count: string
  available_only: boolean
  currency: string
  sort: TourSort
  page: number
}

export function emptyTourSearch(): TourSearchState {
  return {
    keyword: '',
    destination: '',
    min_price: '',
    max_price: '',
    departure_from: '',
    departure_to: '',
    min_duration: '',
    max_duration: '',
    traveler_count: '',
    available_only: false,
    currency: '',
    sort: 'recently_added',
    page: 1,
  }
}

function queryValue(value: LocationQuery[string] | undefined): string {
  const firstValue = Array.isArray(value) ? value[0] : value
  return typeof firstValue === 'string' ? firstValue : ''
}

function parsePage(value: string): number {
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1
}

function parseSort(value: string): TourSort {
  if (
    value === 'earliest_departure'
    || value === 'price_asc'
    || value === 'price_desc'
  ) {
    return value
  }
  return 'recently_added'
}

export function parseTourSearch(query: LocationQuery): TourSearchState {
  return {
    keyword: queryValue(query.keyword),
    destination: queryValue(query.destination),
    min_price: queryValue(query.min_price),
    max_price: queryValue(query.max_price),
    departure_from: queryValue(query.departure_from),
    departure_to: queryValue(query.departure_to),
    min_duration: queryValue(query.min_duration),
    max_duration: queryValue(query.max_duration),
    traveler_count: queryValue(query.traveler_count),
    available_only: queryValue(query.available_only) === 'true',
    currency: queryValue(query.currency).toUpperCase(),
    sort: parseSort(queryValue(query.sort)),
    page: parsePage(queryValue(query.page)),
  }
}

export function tourSearchQuery(
  state: TourSearchState,
  page = state.page,
): LocationQueryRaw {
  const query: LocationQueryRaw = {}
  const textFields: Array<keyof TourSearchFilters> = [
    'keyword',
    'destination',
    'min_price',
    'max_price',
    'departure_from',
    'departure_to',
    'min_duration',
    'max_duration',
    'traveler_count',
    'currency',
  ]

  for (const field of textFields) {
    const value = state[field]
    if (typeof value === 'string' && value.trim()) {
      query[field] = value.trim()
    }
  }
  if (state.available_only) query.available_only = 'true'
  if (state.sort !== 'recently_added') query.sort = state.sort
  if (page > 1) query.page = String(page)

  return query
}

export function tourSearchFilterCount(state: TourSearchState): number {
  const filters = [
    state.keyword,
    state.destination,
    state.min_price,
    state.max_price,
    state.departure_from,
    state.departure_to,
    state.min_duration,
    state.max_duration,
    state.traveler_count,
    state.currency,
    state.available_only,
  ].filter(Boolean).length
  return filters + Number(state.sort !== 'recently_added')
}

export function validateTourSearch(state: TourSearchState): string | null {
  const minimumPrice = state.min_price ? Number(state.min_price) : null
  const maximumPrice = state.max_price ? Number(state.max_price) : null
  if (
    (minimumPrice !== null || maximumPrice !== null)
    && !state.currency
  ) {
    return 'Choose a currency before setting a price range.'
  }
  if (
    (minimumPrice !== null && (!Number.isFinite(minimumPrice) || minimumPrice < 0))
    || (maximumPrice !== null && (!Number.isFinite(maximumPrice) || maximumPrice < 0))
  ) {
    return 'Prices must be zero or greater.'
  }
  if (
    minimumPrice !== null
    && maximumPrice !== null
    && minimumPrice > maximumPrice
  ) {
    return 'Minimum price must not exceed maximum price.'
  }
  if (
    state.departure_from
    && state.departure_to
    && state.departure_from > state.departure_to
  ) {
    return 'Departure start date must not be after the end date.'
  }

  const minimumDuration = state.min_duration
    ? Number(state.min_duration)
    : null
  const maximumDuration = state.max_duration
    ? Number(state.max_duration)
    : null
  const travelers = state.traveler_count
    ? Number(state.traveler_count)
    : null
  if (
    [minimumDuration, maximumDuration, travelers].some(
      (value) => value !== null && (!Number.isInteger(value) || value < 1),
    )
  ) {
    return 'Duration and traveler counts must be positive whole numbers.'
  }
  if (
    minimumDuration !== null
    && maximumDuration !== null
    && minimumDuration > maximumDuration
  ) {
    return 'Minimum duration must not exceed maximum duration.'
  }

  return null
}
