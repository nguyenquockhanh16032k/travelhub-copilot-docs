<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { listTours } from '../services/tours'
import type { PublicTourCard } from '../types/tour'
import {
  emptyTourSearch,
  parseTourSearch,
  tourSearchFilterCount,
  tourSearchQuery,
  validateTourSearch,
  type TourSearchState,
} from '../utils/tourSearch'

const route = useRoute()
const router = useRouter()
const tours = ref<PublicTourCard[]>([])
const filters = ref<TourSearchState>(emptyTourSearch())
const currencies = ref<string[]>([])
const page = ref(1)
const size = 12
const total = ref(0)
const pages = ref(0)
const loading = ref(false)
const error = ref('')
const hasLoaded = ref(false)
let currentRequest: AbortController | undefined
let requestId = 0
let keywordTimer: ReturnType<typeof setTimeout> | undefined

const filterCount = computed(() => tourSearchFilterCount(filters.value))
const currencyOptions = computed(() =>
  [...new Set(['VND', ...currencies.value])]
    .sort((a, b) => {
      if (a === 'VND') return -1
      if (b === 'VND') return 1
      return a.localeCompare(b)
    })
    .map((currency) => ({
      title: currency === 'VND' ? 'VND (preferred)' : currency,
      value: currency,
    })),
)
const activeFilters = computed(() => {
  const active: string[] = []
  const current = filters.value
  if (current.keyword) active.push(`Keyword: ${current.keyword}`)
  if (current.destination) active.push(`Destination: ${current.destination}`)
  if (current.min_price) active.push(`Min price: ${current.min_price}`)
  if (current.max_price) active.push(`Max price: ${current.max_price}`)
  if (current.departure_from) active.push(`From: ${current.departure_from}`)
  if (current.departure_to) active.push(`To: ${current.departure_to}`)
  if (current.min_duration) active.push(`Min days: ${current.min_duration}`)
  if (current.max_duration) active.push(`Max days: ${current.max_duration}`)
  if (current.traveler_count) {
    active.push(`Travelers: ${current.traveler_count}`)
  }
  if (current.currency) active.push(`Currency: ${current.currency}`)
  if (current.available_only) active.push('Available departures only')
  if (current.sort !== 'recently_added') {
    active.push(`Sort: ${current.sort.replaceAll('_', ' ')}`)
  }
  return active
})

async function loadTours(): Promise<void> {
  currentRequest?.abort()
  const controller = new AbortController()
  currentRequest = controller
  const thisRequest = ++requestId
  loading.value = true
  error.value = ''

  const { page: currentPage, ...searchFilters } = filters.value
  try {
    const result = await listTours(
      currentPage,
      size,
      searchFilters,
      controller.signal,
    )
    if (thisRequest !== requestId) return
    tours.value = result.items
    total.value = result.total
    pages.value = result.pages
    currencies.value = result.currencies
    page.value = result.page
  } catch {
    if (controller.signal.aborted || thisRequest !== requestId) return
    tours.value = []
    total.value = 0
    pages.value = 0
    error.value = 'Unable to load tours. Please try again.'
  } finally {
    if (thisRequest === requestId) {
      loading.value = false
      hasLoaded.value = true
    }
  }
}

async function navigateToSearch(
  nextPage: number,
  replace: boolean,
): Promise<void> {
  filters.value.page = nextPage
  page.value = nextPage
  const query = tourSearchQuery(filters.value, nextPage)
  if (JSON.stringify(query) === JSON.stringify(route.query)) {
    await loadTours()
    return
  }
  const location = { path: route.path, query }
  if (replace) await router.replace(location)
  else await router.push(location)
}

function applyFilters(): void {
  if (keywordTimer) clearTimeout(keywordTimer)
  const validationError = validateTourSearch(filters.value)
  if (validationError) {
    error.value = validationError
    return
  }
  void navigateToSearch(1, false)
}

function scheduleKeywordSearch(): void {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => {
    const validationError = validateTourSearch(filters.value)
    if (validationError) {
      error.value = validationError
      return
    }
    void navigateToSearch(1, true)
  }, 350)
}

function clearFilters(): void {
  if (keywordTimer) clearTimeout(keywordTimer)
  filters.value = emptyTourSearch()
  void navigateToSearch(1, false)
}

function changeCurrency(value: string | null): void {
  filters.value.currency = value ?? ''
  filters.value.min_price = ''
  filters.value.max_price = ''
  if (filters.value.sort === 'price_asc' || filters.value.sort === 'price_desc') {
    filters.value.sort = 'recently_added'
  }
}

function changePage(value: number): void {
  void navigateToSearch(value, false)
}

watch(
  () => route.query,
  () => {
    filters.value = parseTourSearch(route.query)
    page.value = filters.value.page
    void loadTours()
  },
  { deep: true, immediate: true },
)

onBeforeUnmount(() => {
  currentRequest?.abort()
  if (keywordTimer) clearTimeout(keywordTimer)
})
</script>

<template>
  <v-container class="py-8">
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold mb-2">Explore tours</h1>
      <p class="text-body-1 text-medium-emphasis">
        Search published tours and eligible departures.
      </p>
    </div>

    <v-card class="mb-5" variant="tonal">
      <v-card-text>
        <form @submit.prevent="applyFilters">
          <v-row>
            <v-col cols="12" sm="6" md="4">
              <v-text-field
                v-model="filters.keyword"
                label="Keyword"
                placeholder="Tour name or details"
                prepend-inner-icon="mdi-magnify"
                hide-details="auto"
                @update:model-value="scheduleKeywordSearch"
              />
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-text-field
                v-model="filters.destination"
                label="Destination"
                placeholder="For example, Da Lat"
                prepend-inner-icon="mdi-map-marker"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-select
                v-model="filters.currency"
                :items="currencyOptions"
                label="Currency (optional)"
                hint="Required for price filters; no conversion is applied."
                persistent-hint
                clearable
                @update:model-value="changeCurrency"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.min_price"
                label="Minimum price"
                type="number"
                min="0"
                step="0.01"
                :disabled="!filters.currency"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.max_price"
                label="Maximum price"
                type="number"
                min="0"
                step="0.01"
                :disabled="!filters.currency"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.departure_from"
                label="Departure from"
                type="date"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.departure_to"
                label="Departure to"
                type="date"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.min_duration"
                label="Min days"
                type="number"
                min="1"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.max_duration"
                label="Max days"
                type="number"
                min="1"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-text-field
                v-model="filters.traveler_count"
                label="Travelers"
                type="number"
                min="1"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="6" sm="3" md="2">
              <v-select
                v-model="filters.sort"
                :items="[
                  { title: 'Recently added', value: 'recently_added' },
                  { title: 'Earliest departure', value: 'earliest_departure' },
                  {
                    title: 'Price: low to high',
                    value: 'price_asc',
                    props: { disabled: !filters.currency },
                  },
                  {
                    title: 'Price: high to low',
                    value: 'price_desc',
                    props: { disabled: !filters.currency },
                  },
                ]"
                label="Sort by"
                hide-details="auto"
              />
            </v-col>
            <v-col cols="12" sm="6" md="4" class="d-flex align-center">
              <v-switch
                v-model="filters.available_only"
                label="Available departures only"
                color="primary"
                hide-details
              />
            </v-col>
            <v-col cols="12" md="8" class="d-flex align-center justify-end ga-2">
              <v-btn
                v-if="filterCount"
                variant="text"
                :disabled="loading"
                @click="clearFilters"
              >
                Clear all
              </v-btn>
              <v-btn
                type="submit"
                color="primary"
                prepend-icon="mdi-magnify"
                :loading="loading"
              >
                Search
              </v-btn>
            </v-col>
          </v-row>
        </form>
      </v-card-text>
    </v-card>

    <div class="d-flex flex-wrap align-center justify-space-between mb-3 ga-2">
      <p class="text-body-2" aria-live="polite">
        {{ total }} {{ total === 1 ? 'tour' : 'tours' }} found
      </p>
      <div v-if="activeFilters.length" class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="activeFilter in activeFilters"
          :key="activeFilter"
          size="small"
          variant="outlined"
        >
          {{ activeFilter }}
        </v-chip>
      </div>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="loadTours">Retry</v-btn>
      </template>
    </v-alert>

    <v-progress-linear
      v-if="loading"
      indeterminate
      class="mb-4"
      aria-label="Loading tours"
    />

    <v-row v-if="!loading && !error && tours.length">
      <v-col v-for="tour in tours" :key="tour.id" cols="12" sm="6" lg="4">
        <v-card height="100%">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon>mdi-map-marker-path</v-icon>
              </v-avatar>
            </template>
            <v-card-title>{{ tour.title }}</v-card-title>
            <v-card-subtitle>{{ tour.destination }}</v-card-subtitle>
          </v-card-item>

          <v-card-text>
            <div class="d-flex flex-wrap ga-2">
              <v-chip size="small" prepend-icon="mdi-clock-outline">
                {{ tour.duration_days }}
                {{ tour.duration_days === 1 ? 'day' : 'days' }}
              </v-chip>
              <v-chip
                size="small"
                :color="tour.has_available_departure ? 'success' : 'default'"
                prepend-icon="mdi-seat"
              >
                {{ tour.has_available_departure ? 'Available' : 'No eligible departures' }}
              </v-chip>
            </div>

            <div v-if="tour.starting_prices.length" class="mt-4">
              <p
                v-for="price in tour.starting_prices"
                :key="price.currency"
                class="text-body-2"
              >
                Starting at {{ price.amount }} {{ price.currency }}
              </p>
            </div>
            <p v-if="tour.next_departure" class="text-body-2 mt-3">
              Next eligible departure: {{ tour.next_departure.start_date }}
              ({{ tour.next_departure.available_seats }} seats shown available at search time)
            </p>
            <p v-if="tour.description" class="mt-4">
              {{ tour.description }}
            </p>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="primary"
              variant="text"
              :to="{ name: 'tour-detail', params: { tourId: tour.id } }"
            >
              Tour details
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-alert
      v-else-if="hasLoaded && !loading && !error"
      type="info"
      variant="tonal"
    >
      No tours match these search criteria. Try changing or clearing the filters.
    </v-alert>

    <v-pagination
      v-if="!loading && !error && pages > 1"
      :model-value="page"
      :length="pages"
      class="mt-6"
      @update:model-value="changePage"
    />
  </v-container>
</template>
