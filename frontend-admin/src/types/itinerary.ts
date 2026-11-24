export interface ItineraryItem {
  id: string
  tour_id: string
  day_number: number
  sequence: number
  activity: string
  time: string | null
  location: string | null
  description: string | null
}

export interface ItineraryPayload {
  day_number: number
  sequence: number
  activity: string
  time: string | null
  location: string | null
  description: string | null
}
