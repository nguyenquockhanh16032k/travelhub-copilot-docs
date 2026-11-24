<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { getMyBooking } from '../services/bookings'
import type { CustomerBooking } from '../types/booking'

const route = useRoute()
const booking = ref<CustomerBooking | null>(null)
const loading = ref(false)
const error = ref('')

async function load(): Promise<void> {
  const bookingId = route.params.bookingId
  if (typeof bookingId !== 'string') {
    error.value = 'Booking not found.'
    return
  }

  loading.value = true
  error.value = ''
  try {
    booking.value = await getMyBooking(bookingId)
  } catch {
    booking.value = null
    error.value = 'Unable to load this booking. It may not be linked to your account.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
watch(() => route.params.bookingId, () => void load())
</script>

<template>
  <v-container class="py-8" style="max-width: 900px">
    <v-btn
      to="/my/bookings"
      variant="text"
      prepend-icon="mdi-arrow-left"
      class="mb-4"
    >
      Back to my bookings
    </v-btn>
    <v-progress-linear v-if="loading" indeterminate class="mb-4" />
    <v-alert v-if="error" type="error" variant="tonal">
      {{ error }}
    </v-alert>

    <template v-if="booking && !loading">
      <div class="d-flex align-center mb-5">
        <div>
          <h1 class="text-h4 font-weight-bold">{{ booking.tour_title }}</h1>
          <p class="text-medium-emphasis">
            {{ booking.destination }} · Booking {{ booking.reference }}
          </p>
        </div>
        <v-spacer />
        <v-chip color="primary">{{ booking.status }}</v-chip>
      </div>

      <v-card title="Departure" class="mb-5">
        <v-card-text>
          <p>
            {{ booking.departure_start_date }} –
            {{ booking.departure_end_date }}
          </p>
          <p class="mt-2">
            {{ booking.duration_days }}
            {{ booking.duration_days === 1 ? 'day' : 'days' }} ·
            {{ booking.passenger_count }}
            {{ booking.passenger_count === 1 ? 'passenger' : 'passengers' }}
          </p>
          <p class="mt-2">
            Booking total: {{ booking.total_amount }} {{ booking.currency }}
          </p>
          <p
            v-if="booking.status === 'pending' && booking.expires_at"
            class="text-medium-emphasis mt-2"
          >
            Pending seat hold expires at
            {{ new Date(booking.expires_at).toLocaleString() }}.
          </p>
        </v-card-text>
      </v-card>

      <v-card title="Payment summary" class="mb-5">
        <v-card-text>
          <p>
            Verified payments:
            {{ booking.verified_paid_amount }} {{ booking.currency }}
          </p>
          <p class="mt-2">
            Outstanding balance:
            {{ booking.outstanding_balance }} {{ booking.currency }}
          </p>
          <p class="mt-2">
            Payment completion: {{ booking.payment_completion_status }}
          </p>
          <p class="text-medium-emphasis mt-3">
            Payment completion and booking confirmation are separate statuses.
          </p>
        </v-card-text>
      </v-card>

      <v-card title="Passengers" class="mb-5">
        <v-list>
          <v-list-item
            v-for="traveler in booking.travelers"
            :key="traveler.id"
            :title="traveler.full_name"
            :subtitle="traveler.traveler_type"
          />
        </v-list>
      </v-card>

      <v-card title="Status history" class="mb-5">
        <v-list v-if="booking.status_history.length">
          <v-list-item
            v-for="(change, index) in booking.status_history"
            :key="`${change.changed_at}-${index}`"
            :title="`${change.old_status ?? 'Created'} → ${change.new_status}`"
            :subtitle="new Date(change.changed_at).toLocaleString()"
          />
        </v-list>
        <v-card-text v-else>No status updates are available.</v-card-text>
      </v-card>

      <v-card title="Recorded payments">
        <v-card-text v-if="!booking.payments.length">
          No payments have been recorded for this booking.
        </v-card-text>
        <v-table v-else>
          <thead>
            <tr>
              <th>Recorded</th>
              <th>Amount</th>
              <th>Method</th>
              <th>Status</th>
              <th>Reference</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="payment in booking.payments" :key="payment.id">
              <td>{{ new Date(payment.recorded_at).toLocaleString() }}</td>
              <td>{{ payment.amount }} {{ payment.currency }}</td>
              <td>{{ payment.method.replace('_', ' ') }}</td>
              <td>{{ payment.status }}</td>
              <td>{{ payment.transaction_reference || '—' }}</td>
            </tr>
          </tbody>
        </v-table>
        <v-card-text class="text-medium-emphasis">
          These are payment records entered by TravelHub. No payment is
          processed on this page.
        </v-card-text>
      </v-card>
    </template>
  </v-container>
</template>
