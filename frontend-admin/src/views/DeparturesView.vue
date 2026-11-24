<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import {
  createDeparture,
  listDepartures,
  updateDeparture,
} from '../services/departures'
import { listTours } from '../services/tours'
import type {
  Departure,
  DepartureCreatePayload,
  DepartureStatus,
  Tour,
} from '../types/catalog'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const canManageDepartures = computed(() =>
  hasPermission(auth.user?.roles, 'departures:write'),
)
const departures = ref<Departure[]>([])
const tours = ref<Tour[]>([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const editing = ref<Departure | null>(null)
const form = ref<DepartureCreatePayload>({
  tour_id: '',
  start_date: '',
  end_date: '',
  capacity: 1,
  price: '0',
  currency: 'VND',
  status: 'draft',
})

const statuses: DepartureStatus[] = [
  'draft',
  'open',
  'closed',
  'completed',
  'cancelled',
]

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const [departureResult, tourResult] = await Promise.all([
      listDepartures(page.value, size.value),
      listTours(1, 100),
    ])
    departures.value = departureResult.items
    total.value = departureResult.total
    tours.value = tourResult.items
  } catch {
    error.value = 'Unable to load departures.'
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editing.value = null
  form.value = {
    tour_id: '',
    start_date: '',
    end_date: '',
    capacity: 1,
    price: '0',
    currency: 'VND',
    status: 'draft',
  }
  dialog.value = true
}

function openCapacityEditor(departure: Departure): void {
  editing.value = departure
  form.value = {
    tour_id: departure.tour_id,
    start_date: departure.start_date,
    end_date: departure.end_date,
    capacity: departure.capacity,
    price: departure.price,
    currency: departure.currency,
    status: departure.status,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (editing.value) {
      await updateDeparture(editing.value.id, {
        start_date: form.value.start_date,
        end_date: form.value.end_date,
        capacity: form.value.capacity,
        price: form.value.price,
        currency: form.value.currency,
        status: form.value.status,
      })
      success.value = 'Departure updated successfully.'
    } else {
      await createDeparture(form.value)
      success.value = 'Departure created successfully.'
    }
    dialog.value = false
    await load()
  } catch {
    error.value =
      editing.value
        ? 'Unable to update departure.'
        : 'Unable to create departure.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Departures</h1>
      <v-spacer />
      <v-btn
        v-if="canManageDepartures"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreate"
      >
        Create departure
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-else-if="!departures.length" type="info" variant="tonal">
      No departures found.
    </v-alert>
    <v-table v-else>
      <thead>
        <tr>
          <th>Dates</th>
          <th>Capacity</th>
          <th>Available</th>
          <th>Price</th>
          <th>Status</th>
          <th v-if="canManageDepartures" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="departure in departures" :key="departure.id">
          <td>{{ departure.start_date }} – {{ departure.end_date }}</td>
          <td>{{ departure.capacity }}</td>
          <td>{{ departure.available_seats }}</td>
          <td>{{ departure.price }} {{ departure.currency }}</td>
          <td>{{ departure.status }}</td>
          <td v-if="canManageDepartures">
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openCapacityEditor(departure)"
            >
              Manage
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <v-pagination
      v-if="total > size"
      v-model="page"
      :length="Math.ceil(total / size)"
      class="mt-4"
      @update:model-value="load"
    />

    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editing ? 'Manage departure' : 'Create departure' }}
        </v-card-title>
        <v-card-text>
          <v-select
            v-model="form.tour_id"
            label="Tour"
            :items="tours"
            item-title="title"
            item-value="id"
            :disabled="editing !== null"
          />
          <v-text-field v-model="form.start_date" label="Start date" type="date" />
          <v-text-field v-model="form.end_date" label="End date" type="date" />
          <v-text-field
            v-model.number="form.capacity"
            label="Capacity"
            type="number"
            min="1"
          />
          <v-text-field v-model="form.price" label="Price" type="number" min="0" />
          <v-text-field v-model="form.currency" label="Currency" maxlength="3" />
          <v-select v-model="form.status" label="Status" :items="statuses" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="loading" @click="submit">
            {{ editing ? 'Save' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
