export type TourStatus = 'draft' | 'published' | 'archived'

export interface Tour {
  id: string
  title: string
  slug: string
  description: string | null
  duration_days: number
  destination: string
  status: TourStatus
}

export interface TourPage {
  items: Tour[]
  total: number
  page: number
  size: number
  pages: number
}

export interface TourCreatePayload {
  title: string
  slug: string
  description: string | null
  duration_days: number
  destination: string
  status: TourStatus
}

export type TourUpdatePayload = Partial<TourCreatePayload>

export type DepartureStatus =
  | 'draft'
  | 'open'
  | 'closed'
  | 'completed'
  | 'cancelled'

export interface Departure {
  id: string
  tour_id: string
  start_date: string
  end_date: string
  capacity: number
  available_seats: number
  price: string
  currency: string
  status: DepartureStatus
}

export interface DeparturePage {
  items: Departure[]
  total: number
  page: number
  size: number
  pages: number
}

export interface AdminDeparture extends Departure {
  tour_title: string
}

export interface AdminDeparturePage extends DeparturePage {
  items: AdminDeparture[]
}

export interface DepartureCreatePayload {
  tour_id: string
  start_date: string
  end_date: string
  capacity: number
  price: string
  currency: string
  status: DepartureStatus
}

export interface DepartureUpdatePayload {
  start_date?: string
  end_date?: string
  capacity?: number
  price?: string
  currency?: string
  status?: DepartureStatus
}
