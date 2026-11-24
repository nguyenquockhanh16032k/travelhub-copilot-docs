import type { Departure } from '../types/tour'

export function listBookableDepartures(
  departures: Departure[],
): Departure[] {
  return departures
    .filter(
      (departure) =>
        departure.status === 'open' &&
        departure.available_seats > 0,
    )
    .sort((left, right) => left.start_date.localeCompare(right.start_date))
}
