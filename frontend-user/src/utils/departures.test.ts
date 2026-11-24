import { describe, expect, it } from 'vitest'

import type { Departure } from '../types/tour'
import { listBookableDepartures } from './departures'

describe('listBookableDepartures', () => {
  it('filters sold-out departures and sorts backend-eligible options', () => {
    const departures: Departure[] = [
      {
        id: 'later',
        tour_id: 'tour',
        start_date: '2027-01-20',
        end_date: '2027-01-22',
        capacity: 10,
        available_seats: 2,
        price: '100.00',
        currency: 'VND',
        status: 'open',
      },
      {
        id: 'sold-out',
        tour_id: 'tour',
        start_date: '2027-01-10',
        end_date: '2027-01-12',
        capacity: 10,
        available_seats: 0,
        price: '100.00',
        currency: 'VND',
        status: 'open',
      },
      {
        id: 'soon',
        tour_id: 'tour',
        start_date: '2027-01-10',
        end_date: '2027-01-12',
        capacity: 10,
        available_seats: 1,
        price: '100.00',
        currency: 'VND',
        status: 'open',
      },
    ]

    expect(listBookableDepartures(departures).map(({ id }) => id)).toEqual([
      'soon',
      'later',
    ])
  })
})
