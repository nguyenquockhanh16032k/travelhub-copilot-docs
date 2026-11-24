<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getTour } from '../services/tours'
import type { Departure, TourDetail } from '../types/tour'
import { listBookableDepartures } from '../utils/departures'

const route = useRoute()
const router = useRouter()
const tour = ref<TourDetail | null>(null)
const selectedDepartureId = ref('')
const loading = ref(false)
const error = ref('')

const bookableDepartures = computed(() =>
  listBookableDepartures(tour.value?.departures ?? []),
)
const selectedDeparture = computed(
  () =>
    bookableDepartures.value.find(
      (departure) => departure.id === selectedDepartureId.value,
    ) ?? null,
)
const itineraryDays = computed(() =>
  [...new Set((tour.value?.itinerary ?? []).map((item) => item.day_number))].sort(
    (left, right) => left - right,
  ),
)

function itineraryItemsForDay(dayNumber: number) {
  return (tour.value?.itinerary ?? [])
    .filter((item) => item.day_number === dayNumber)
    .sort((left, right) => left.sequence - right.sequence)
}

function formatDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString()
}

async function load(): Promise<void> {
  const tourId = route.params.tourId
  if (typeof tourId !== 'string' || !tourId) {
    error.value = 'Tour not found.'
    return
  }

  loading.value = true
  error.value = ''
  try {
    tour.value = await getTour(tourId)
  } catch {
    error.value = 'Unable to load this tour. It may no longer be available.'
  } finally {
    loading.value = false
  }
}

function continueToBooking(departure: Departure): void {
  if (!tour.value) return
  void router.push({
    path: '/booking/new',
    query: {
      tourId: tour.value.id,
      departureId: departure.id,
    },
  })
}

onMounted(() => {
  void load()
})
</script>

<template>
  <v-container class="py-8">
    <v-btn to="/tours" variant="text" prepend-icon="mdi-arrow-left" class="mb-4">
      All tours
    </v-btn>

    <v-progress-linear v-if="loading" indeterminate class="mb-4" />
    <v-alert v-else-if="error" type="error" variant="tonal">
      {{ error }}
      <template #append>
        <v-btn to="/tours" variant="text">Browse tours</v-btn>
      </template>
    </v-alert>

    <template v-else-if="tour">
      <h1 class="text-h3 font-weight-bold mb-2">{{ tour.title }}</h1>
      <p class="text-h6 text-medium-emphasis mb-4">
        <v-icon class="mr-1">mdi-map-marker</v-icon>
        {{ tour.destination }}
        <span class="mx-2">·</span>
        {{ tour.duration_days }}
        {{ tour.duration_days === 1 ? 'day' : 'days' }}
      </p>
      <p v-if="tour.description" class="text-body-1 mb-8">
        {{ tour.description }}
      </p>

      <v-card v-if="tour.itinerary.length" title="Itinerary" class="mb-6">
        <v-card-text>
          <section
            v-for="day in itineraryDays"
            :key="day"
            class="mb-5"
          >
            <h2 class="text-h6 mb-2">Day {{ day }}</h2>
            <v-list density="compact">
              <v-list-item
                v-for="item in itineraryItemsForDay(day)"
                :key="item.id"
                :title="item.activity"
                :subtitle="[
                  item.time,
                  item.location,
                  item.description,
                ].filter(Boolean).join(' · ')"
              />
            </v-list>
          </section>
        </v-card-text>
      </v-card>

      <v-card title="Available departures">
        <v-card-text v-if="!bookableDepartures.length">
          <v-alert type="info" variant="tonal">
            There are no upcoming departures with seats currently available.
          </v-alert>
        </v-card-text>
        <v-radio-group
          v-else
          v-model="selectedDepartureId"
          class="px-4"
          hide-details
        >
          <v-radio
            v-for="departure in bookableDepartures"
            :key="departure.id"
            :value="departure.id"
          >
            <template #label>
              <div>
                <div>
                  {{ formatDate(departure.start_date) }} –
                  {{ formatDate(departure.end_date) }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ departure.available_seats }} seats available ·
                  {{ departure.price }} {{ departure.currency }} per traveler
                </div>
              </div>
            </template>
          </v-radio>
        </v-radio-group>
        <v-card-actions v-if="bookableDepartures.length">
          <v-spacer />
          <v-btn
            color="primary"
            :disabled="!selectedDeparture"
            @click="selectedDeparture && continueToBooking(selectedDeparture)"
          >
            Continue to booking
          </v-btn>
        </v-card-actions>
      </v-card>
    </template>
  </v-container>
</template>
