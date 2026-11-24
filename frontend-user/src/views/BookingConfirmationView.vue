<script setup lang="ts">
import { computed } from 'vue'

import { useBookingConfirmationStore } from '../stores/bookingConfirmation'

const confirmationStore = useBookingConfirmationStore()
const confirmation = computed(() => confirmationStore.confirmation)

const statusMessage = computed(() => {
  if (!confirmation.value) return ''
  if (confirmation.value.status === 'pending') {
    return 'Your request is pending review and is not confirmed yet.'
  }
  if (confirmation.value.status === 'confirmed') {
    return 'Your booking is confirmed.'
  }
  return `Current booking status: ${confirmation.value.status}.`
})
</script>

<template>
  <v-container class="py-12" style="max-width: 720px">
    <v-card v-if="confirmation" class="pa-4">
      <v-card-item>
        <template #prepend>
          <v-avatar color="success" variant="tonal">
            <v-icon>mdi-check</v-icon>
          </v-avatar>
        </template>
        <v-card-title>Booking request received</v-card-title>
      </v-card-item>
      <v-card-text>
        <v-alert
          :type="confirmation.status === 'confirmed' ? 'success' : 'info'"
          variant="tonal"
          class="mb-4"
        >
          {{ statusMessage }}
        </v-alert>
        <p><strong>Reference:</strong> {{ confirmation.reference }}</p>
        <p class="mt-2">
          <strong>Booking total:</strong>
          {{ confirmation.total_amount }} {{ confirmation.currency }}
        </p>
        <p class="text-medium-emphasis mt-4">
          Bookings linked to your customer profile are available in My bookings
          after you sign in. Guest bookings are not available in booking
          history; keep this reference for your records.
        </p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn to="/my/bookings" variant="text">My bookings</v-btn>
        <v-btn to="/tours" color="primary">Explore more tours</v-btn>
      </v-card-actions>
    </v-card>

    <v-card v-else class="pa-4">
      <v-card-title>Booking details unavailable</v-card-title>
      <v-card-text>
        This confirmation is no longer available in this browser session.
        Browse tours to start a new booking request.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn to="/tours" color="primary">Browse tours</v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>
