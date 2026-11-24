<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import { getDashboardSummary } from '../services/dashboard'
import type { DashboardSummary } from '../types/dashboard'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const canViewFinancials = computed(() =>
  hasPermission(auth.user?.roles, 'payments:read'),
)
const summary = ref<DashboardSummary | null>(null)
const loading = ref(false)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    summary.value = await getDashboardSummary()
  } catch {
    error.value = 'Unable to load the dashboard summary.'
  } finally {
    loading.value = false
  }
}

function formatAmount(amount: string, currency: string): string {
  return `${amount} ${currency}`
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Dashboard</h1>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="load">Retry</v-btn>
      </template>
    </v-alert>

    <v-progress-linear v-if="loading" indeterminate class="mb-4" />

    <template v-if="summary">
      <v-row class="mb-4">
        <v-col cols="12" sm="6">
          <v-card title="Bookings" :subtitle="`${summary.booking_count} total`">
            <v-card-text>
              {{ summary.pending_booking_count }} pending
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-card title="Upcoming departures" class="mb-4">
        <v-card-text v-if="!summary.upcoming_departures.length">
          <v-alert type="info" variant="tonal">
            No upcoming open departures.
          </v-alert>
        </v-card-text>
        <v-table v-else>
          <thead>
            <tr>
              <th>Tour</th>
              <th>Dates</th>
              <th>Available seats</th>
              <th v-if="canViewFinancials">Price</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="departure in summary.upcoming_departures"
              :key="departure.id"
            >
              <td>{{ departure.tour_title }}</td>
              <td>{{ departure.start_date }} – {{ departure.end_date }}</td>
              <td>{{ departure.available_seats }}</td>
              <td v-if="canViewFinancials && departure.price && departure.currency">
                {{ formatAmount(departure.price, departure.currency) }}
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <v-card
        v-if="canViewFinancials && summary.payments_by_currency"
        title="Payment records by currency"
      >
        <v-card-text v-if="!summary.payments_by_currency.length">
          <v-alert type="info" variant="tonal">No payment records yet.</v-alert>
        </v-card-text>
        <v-table v-else>
          <thead>
            <tr>
              <th>Currency</th>
              <th>Payments marked paid</th>
              <th>Payments pending</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="payment in summary.payments_by_currency"
              :key="payment.currency"
            >
              <td>{{ payment.currency }}</td>
              <td>{{ formatAmount(payment.paid_amount, payment.currency) }}</td>
              <td>{{ formatAmount(payment.pending_amount, payment.currency) }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </template>
  </div>
</template>
