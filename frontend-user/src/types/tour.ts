export interface Tour {
  id: string
  title: string
  slug: string
  description: string | null
  duration_days: number
  destination: string
  status: 'published'
}

export interface TourPage {
  items: PublicTourCard[]
  total: number
  page: number
  size: number
  pages: number
  currencies: string[]
}

export interface PublicTourCard extends Tour {
  starting_prices: Array<{
    currency: string
    amount: string
  }>
  next_departure: {
    id: string
    start_date: string
    end_date: string
    available_seats: number
    price: string
    currency: string
  } | null
  has_available_departure: boolean
}

export interface TourSearchFilters {
  keyword?: string
  destination?: string
  min_price?: string
  max_price?: string
  departure_from?: string
  departure_to?: string
  min_duration?: string
  max_duration?: string
  traveler_count?: string
  available_only?: boolean
  currency?: string
  sort?: string
}

export interface Departure {
  id: string
  tour_id: string
  start_date: string
  end_date: string
  capacity: number
  available_seats: number
  price: string
  currency: string
  status: 'open'
}

export interface TourDetail extends Tour {
  departures: Departure[]
  itinerary: Array<{
    id: string
    tour_id: string
    day_number: number
    sequence: number
    activity: string
    time: string | null
    location: string | null
    description: string | null
  }>
}
