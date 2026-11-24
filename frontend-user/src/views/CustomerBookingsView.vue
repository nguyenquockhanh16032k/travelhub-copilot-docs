<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { listMyBookings } from '../services/bookings'
import type { CustomerBooking } from '../types/booking'
import axios from 'axios'

const bookings = ref<CustomerBooking[]>([])
const page = ref(1)
const size = 20
const total = ref(0)
const loading = ref(false)
const error = ref('')
const loaded = ref(false)
const now = new Date()
const today = [
  now.getFullYear(),
  String(now.getMonth() + 1).padStart(2, '0'),
  String(now.getDate()).padStart(2, '0'),
].join('-')

const upcoming = computed(() =>
  bookings.value.filter(
    (booking) =>
      booking.departure_start_date >= today &&
      ['pending', 'confirmed'].includes(booking.status),
  ),
)
const completed = computed(() =>
  bookings.value.filter(
    (booking) =>
      booking.status === 'completed' ||
      booking.departure_status === 'completed',
  ),
)
const otherBookings = computed(() =>
  bookings.value.filter(
    (booking) =>
      !upcoming.value.includes(booking) && !completed.value.includes(booking),
  ),
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listMyBookings(page.value, size)
    bookings.value = result.items
    total.value = result.total
  } catch (caught) {
    const data: unknown = axios.isAxiosError(caught)
      ? caught.response?.data
      : undefined
    const detail =
      typeof data === 'object' && data !== null && 'detail' in data
        ? data.detail
        : undefined
    const code =
      typeof detail === 'object' && detail !== null && 'code' in detail
        ? detail.code
        : undefined
    error.value =
      code === 'CUSTOMER_PROFILE_NOT_LINKED'
        ? 'Your customer account is not linked to a profile yet. Please contact TravelHub support.'
        : 'Unable to load your bookings. Please try again.'
  } finally {
    loading.value = false
    loaded.value = true
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <v-container class="py-8" style="max-width: 1000px">
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">My bookings</h1>
        <p class="text-medium-emphasis mt-1">
          Bookings linked to your customer profile.
        </p>
      </div>
      <v-spacer />
      <v-btn to="/tours" variant="outlined">Explore tours</v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="load">Retry</v-btn>
      </template>
    </v-alert>
    <v-progress-linear v-if="loading" indeterminate class="mb-4" />

    <template v-if="!loading && !error && bookings.length">
      <section v-if="upcoming.length" class="mb-8">
        <h2 class="text-h5 mb-3">Upcoming tours</h2>
        <v-row>
          <v-col
            v-for="booking in upcoming"
            :key="booking.id"
            cols="12"
            md="6"
          >
            <v-card>
              <v-card-title>{{ booking.tour_title }}</v-card-title>
              <v-card-subtitle>
                {{ booking.destination }} · {{ booking.duration_days }}
                {{ booking.duration_days === 1 ? 'day' : 'days' }}
              </v-card-subtitle>
              <v-card-text>
                <p>
                  {{ booking.departure_start_date }} –
                  {{ booking.departure_end_date }}
                </p>
                <v-chip class="mt-3" size="small" color="primary">
                  {{ booking.status }}
                </v-chip>
                <p class="text-caption mt-3">
                  Reference: {{ booking.reference }}
                </p>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn
                  color="primary"
                  variant="text"
                  :to="`/my/bookings/${booking.id}`"
                >
                  Booking details
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </section>

      <section v-if="completed.length" class="mb-8">
        <h2 class="text-h5 mb-3">Completed tours</h2>
        <v-list lines="two" border rounded>
          <v-list-item
            v-for="booking in completed"
            :key="booking.id"
            :title="booking.tour_title"
            :subtitle="`${booking.departure_start_date} – ${booking.departure_end_date} · ${booking.reference}`"
            :to="`/my/bookings/${booking.id}`"
            append-icon="mdi-chevron-right"
          >
            <template #prepend>
              <v-icon color="success">mdi-check-circle-outline</v-icon>
            </template>
          </v-list-item>
        </v-list>
      </section>

      <section v-if="otherBookings.length">
        <h2 class="text-h5 mb-3">Other bookings</h2>
        <v-list lines="two" border rounded>
          <v-list-item
            v-for="booking in otherBookings"
            :key="booking.id"
            :title="booking.tour_title"
            :subtitle="`${booking.departure_start_date} – ${booking.departure_end_date} · ${booking.reference}`"
            :to="`/my/bookings/${booking.id}`"
            append-icon="mdi-chevron-right"
          >
            <template #prepend>
              <v-chip size="small">{{ booking.status }}</v-chip>
            </template>
          </v-list-item>
        </v-list>
      </section>
    </template>

    <v-alert
      v-else-if="loaded && !loading && !error"
      type="info"
      variant="tonal"
    >
      No bookings are linked to your customer profile.
    </v-alert>

    <v-pagination
      v-if="!loading && !error && total > size"
      v-model="page"
      :length="Math.ceil(total / size)"
      class="mt-6"
      @update:model-value="load"
    />
  </v-container>
</template>
