<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'

import { createBooking } from '../services/bookings'
import { getTour } from '../services/tours'
import { useBookingConfirmationStore } from '../stores/bookingConfirmation'
import type { TravelerInput, BookingCreatePayload } from '../types/booking'
import type { TourDetail } from '../types/tour'
import { listBookableDepartures } from '../utils/departures'
import { multiplyMoney } from '../utils/money'

interface FormValidation {
  valid: boolean
}

interface BookingForm {
  validate: () => Promise<FormValidation>
}

const route = useRoute()
const router = useRouter()
const confirmationStore = useBookingConfirmationStore()
const formRef = ref<BookingForm | null>(null)
const tour = ref<TourDetail | null>(null)
const contactName = ref('')
const contactEmail = ref('')
const contactPhone = ref('')
const travelers = ref<TravelerInput[]>([
  { full_name: '', traveler_type: 'adult' },
])
const loading = ref(false)
const submitting = ref(false)
const error = ref('')

const departure = computed(() => {
  const departureId = route.query.departureId
  if (typeof departureId !== 'string') return null
  return (
    listBookableDepartures(tour.value?.departures ?? []).find(
      (item) => item.id === departureId,
    ) ?? null
  )
})
const canAddTraveler = computed(
  () =>
    departure.value !== null &&
    travelers.value.length < Math.min(departure.value.available_seats, 100),
)
const totalEstimate = computed(() =>
  departure.value
    ? `${multiplyMoney(departure.value.price, travelers.value.length)} ${departure.value.currency}`
    : '',
)

const requiredRule = (value: string): true | string =>
  Boolean(value?.trim()) || 'This field is required.'
const emailRule = (value: string): true | string =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) || 'Enter a valid email address.'

function apiErrorMessage(caught: unknown): string {
  if (axios.isAxiosError(caught)) {
    const data: unknown = caught.response?.data
    if (typeof data === 'object' && data !== null && 'detail' in data) {
      const detail = data.detail
      if (
        typeof detail === 'object' &&
        detail !== null &&
        'message' in detail &&
        typeof detail.message === 'string'
      ) {
        return detail.message
      }
    }
  }
  return 'Unable to submit your booking request. Please try again.'
}

async function load(): Promise<void> {
  confirmationStore.clearConfirmation()
  const tourId = route.query.tourId
  const departureId = route.query.departureId
  if (typeof tourId !== 'string' || typeof departureId !== 'string') {
    error.value = 'Select an available departure before booking.'
    return
  }

  loading.value = true
  error.value = ''
  try {
    tour.value = await getTour(tourId)
    if (
      !listBookableDepartures(tour.value.departures).some(
        (item) => item.id === departureId,
      )
    ) {
      error.value = 'This departure is no longer available. Please choose another.'
    }
  } catch {
    error.value = 'Unable to verify this departure. Please choose a tour again.'
  } finally {
    loading.value = false
  }
}

function addTraveler(): void {
  if (!canAddTraveler.value) return
  travelers.value.push({ full_name: '', traveler_type: 'adult' })
}

function removeTraveler(index: number): void {
  if (travelers.value.length > 1) {
    travelers.value.splice(index, 1)
  }
}

async function submitBooking(): Promise<void> {
  if (!departure.value || !tour.value) return

  const validation = await formRef.value?.validate()
  if (!validation?.valid) return

  submitting.value = true
  error.value = ''
  const payload: BookingCreatePayload = {
    departure_id: departure.value.id,
    contact_name: contactName.value.trim(),
    contact_email: contactEmail.value.trim(),
    contact_phone: contactPhone.value.trim(),
    travelers: travelers.value.map((traveler) => ({
      full_name: traveler.full_name.trim(),
      traveler_type: traveler.traveler_type.trim(),
    })),
    notes: null,
  }

  try {
    const booking = await createBooking(payload)
    confirmationStore.setConfirmation(booking)
    await router.push('/booking/confirmation')
  } catch (caught) {
    error.value = apiErrorMessage(caught)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <v-container class="py-8" style="max-width: 900px">
    <v-btn to="/tours" variant="text" prepend-icon="mdi-arrow-left" class="mb-4">
      Back to tours
    </v-btn>

    <h1 class="text-h4 font-weight-bold mb-6">Request a booking</h1>

    <v-progress-linear v-if="loading" indeterminate class="mb-4" />
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn
          v-if="tour"
          :to="{ name: 'tour-detail', params: { tourId: tour.id } }"
          variant="text"
        >
          Choose another departure
        </v-btn>
        <v-btn v-else to="/tours" variant="text">Browse tours</v-btn>
      </template>
    </v-alert>

    <template v-if="!loading && departure && tour">
      <v-card class="mb-6">
        <v-card-title>{{ tour.title }}</v-card-title>
        <v-card-text>
          <p>
            {{ departure.start_date }} – {{ departure.end_date }}
          </p>
          <p>
            {{ departure.price }} {{ departure.currency }} per traveler
          </p>
          <p>
            Estimated booking total:
            <strong>{{ totalEstimate }}</strong>
          </p>
          <p class="text-medium-emphasis">
            The final total and request status will be returned by TravelHub.
            Submitting this request does not confirm the booking.
          </p>
        </v-card-text>
      </v-card>

      <v-form ref="formRef" @submit.prevent="submitBooking">
        <v-card title="Contact details" class="mb-6">
          <v-card-text>
            <v-text-field
              v-model="contactName"
              label="Contact name"
              maxlength="255"
              :rules="[requiredRule]"
              required
            />
            <v-text-field
              v-model="contactEmail"
              label="Email"
              type="email"
              maxlength="255"
              :rules="[requiredRule, emailRule]"
              required
            />
            <v-text-field
              v-model="contactPhone"
              label="Phone"
              maxlength="50"
              :rules="[requiredRule]"
              required
            />
          </v-card-text>
        </v-card>

        <v-card title="Traveler details" class="mb-6">
          <v-card-text>
            <v-row
              v-for="(traveler, index) in travelers"
              :key="index"
              align="center"
            >
              <v-col cols="12" sm="5">
                <v-text-field
                  v-model="traveler.full_name"
                  :label="`Traveler ${index + 1} full name`"
                  maxlength="255"
                  :rules="[requiredRule]"
                  required
                />
              </v-col>
              <v-col cols="9" sm="5">
                <v-text-field
                  v-model="traveler.traveler_type"
                  label="Traveler type"
                  placeholder="adult"
                  maxlength="20"
                  :rules="[requiredRule]"
                  required
                />
              </v-col>
              <v-col cols="3" sm="2">
                <v-btn
                  v-if="travelers.length > 1"
                  icon="mdi-delete-outline"
                  variant="text"
                  color="error"
                  :aria-label="`Remove traveler ${index + 1}`"
                  @click="removeTraveler(index)"
                />
              </v-col>
            </v-row>
            <v-btn
              variant="outlined"
              prepend-icon="mdi-account-plus"
              :disabled="!canAddTraveler"
              @click="addTraveler"
            >
              Add traveler
            </v-btn>
            <p class="text-caption text-medium-emphasis mt-2">
              Up to {{ Math.min(departure.available_seats, 100) }} travelers for
              this request.
            </p>
          </v-card-text>
        </v-card>

        <div class="d-flex justify-end">
          <v-btn
            type="submit"
            color="primary"
            size="large"
            :loading="submitting"
            :disabled="!departure"
          >
            Submit booking request
          </v-btn>
        </div>
      </v-form>
    </template>
  </v-container>
</template>
