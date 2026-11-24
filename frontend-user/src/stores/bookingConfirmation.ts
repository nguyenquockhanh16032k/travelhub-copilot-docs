import { defineStore } from 'pinia'
import { ref } from 'vue'

import type {
  BookingConfirmation,
  BookingResponse,
} from '../types/booking'

export const useBookingConfirmationStore = defineStore(
  'bookingConfirmation',
  () => {
    const confirmation = ref<BookingConfirmation | null>(null)

    function setConfirmation(booking: BookingResponse): void {
      confirmation.value = {
        reference: booking.reference,
        status: booking.status,
        total_amount: booking.total_amount,
        currency: booking.currency,
      }
    }

    function clearConfirmation(): void {
      confirmation.value = null
    }

    return { confirmation, setConfirmation, clearConfirmation }
  },
)
