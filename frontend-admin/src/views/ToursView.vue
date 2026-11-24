<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import { createTour, listTours, updateTour } from '../services/tours'
import type { Tour, TourCreatePayload, TourStatus } from '../types/catalog'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const canManageTours = computed(() =>
  hasPermission(auth.user?.roles, 'tours:write'),
)
const tours = ref<Tour[]>([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const success = ref('')
const destinationFilter = ref('')
const dialog = ref(false)
const editing = ref<Tour | null>(null)
const form = ref<TourCreatePayload>({
  title: '',
  slug: '',
  description: null,
  duration_days: 1,
  destination: '',
  status: 'draft',
})

const statuses: TourStatus[] = ['draft', 'published', 'archived']

async function loadTours(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listTours(
      page.value,
      size.value,
      destinationFilter.value,
    )
    tours.value = result.items
    total.value = result.total
  } catch {
    error.value = 'Unable to load tours.'
  } finally {
    loading.value = false
  }
}

async function submitTour(): Promise<void> {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (editing.value) {
      await updateTour(editing.value.id, form.value)
      success.value = 'Tour updated successfully.'
    } else {
      await createTour(form.value)
      success.value = 'Tour created successfully.'
    }
    dialog.value = false
    await loadTours()
  } catch {
    error.value = editing.value
      ? 'Unable to update tour. Check the title, slug, and details.'
      : 'Unable to create tour. Check the title, slug, and details.'
  } finally {
    loading.value = false
  }
}

function openCreateDialog(): void {
  editing.value = null
  form.value = {
    title: '',
    slug: '',
    description: null,
    duration_days: 1,
    destination: '',
    status: 'draft',
  }
  dialog.value = true
}

function openEditDialog(tour: Tour): void {
  editing.value = tour
  form.value = {
    title: tour.title,
    slug: tour.slug,
    description: tour.description,
    duration_days: tour.duration_days,
    destination: tour.destination,
    status: tour.status,
  }
  dialog.value = true
}

onMounted(() => {
  void loadTours()
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Tours</h1>
      <v-spacer />
      <v-btn
        v-if="canManageTours"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        Create tour
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-text-field
      v-model="destinationFilter"
      label="Filter by destination"
      prepend-inner-icon="mdi-magnify"
      clearable
      class="mb-4"
      @keyup.enter="loadTours"
    />

    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-else-if="!tours.length" type="info" variant="tonal">
      No tours found.
    </v-alert>
    <v-table v-else>
      <thead>
        <tr>
          <th>Title</th>
          <th>Slug</th>
          <th>Destination</th>
          <th>Duration</th>
          <th>Status</th>
          <th v-if="canManageTours" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="tour in tours" :key="tour.id">
          <td>{{ tour.title }}</td>
          <td>{{ tour.slug }}</td>
          <td>{{ tour.destination }}</td>
          <td>{{ tour.duration_days }} days</td>
          <td>{{ tour.status }}</td>
          <td v-if="canManageTours">
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openEditDialog(tour)"
            >
              Edit
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
      @update:model-value="loadTours"
    />

    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>{{ editing ? 'Edit tour' : 'Create tour' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.title" label="Title" required />
          <v-text-field v-model="form.slug" label="Slug" required />
          <v-text-field v-model="form.destination" label="Destination" required />
          <v-text-field
            v-model.number="form.duration_days"
            label="Duration days"
            type="number"
            min="1"
            required
          />
          <v-textarea v-model="form.description" label="Description" />
          <v-select
            v-model="form.status"
            label="Status"
            :items="statuses"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="loading" @click="submitTour">
            {{ editing ? 'Save changes' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
