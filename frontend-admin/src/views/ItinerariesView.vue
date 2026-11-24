<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import {
  createItineraryItem,
  deleteItineraryItem,
  listItineraries,
  updateItineraryItem,
} from '../services/itineraries'
import { listTours } from '../services/tours'
import type { ItineraryItem, ItineraryPayload } from '../types/itinerary'
import type { Tour } from '../types/catalog'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const canManageItineraries = computed(() =>
  hasPermission(auth.user?.roles, 'itineraries:write'),
)
const tours = ref<Tour[]>([])
const items = ref<ItineraryItem[]>([])
const selectedTourId = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const deleteDialog = ref(false)
const editing = ref<ItineraryItem | null>(null)
const deleting = ref<ItineraryItem | null>(null)
const form = ref<ItineraryPayload>({
  day_number: 1,
  sequence: 1,
  activity: '',
  time: null,
  location: null,
  description: null,
})

async function loadItems(): Promise<void> {
  if (!selectedTourId.value) {
    items.value = []
    return
  }
  items.value = await listItineraries(selectedTourId.value)
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listTours(1, 100)
    tours.value = result.items
    if (!tours.value.some((tour) => tour.id === selectedTourId.value)) {
      selectedTourId.value = tours.value[0]?.id ?? ''
    }
    await loadItems()
  } catch {
    items.value = []
    error.value = 'Unable to load tours or itinerary items.'
  } finally {
    loading.value = false
  }
}

async function changeTour(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await loadItems()
  } catch {
    items.value = []
    error.value = 'Unable to load this tour itinerary.'
  } finally {
    loading.value = false
  }
}

function resetForm(): void {
  editing.value = null
  const dayItems = items.value.filter((item) => item.day_number === 1)
  form.value = {
    day_number: 1,
    sequence:
      dayItems.reduce((highest, item) => Math.max(highest, item.sequence), 0) +
      1,
    activity: '',
    time: null,
    location: null,
    description: null,
  }
}

function openCreate(): void {
  resetForm()
  dialog.value = true
}

function openEdit(item: ItineraryItem): void {
  editing.value = item
  form.value = {
    day_number: item.day_number,
    sequence: item.sequence,
    activity: item.activity,
    time: item.time,
    location: item.location,
    description: item.description,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  if (
    !selectedTourId.value ||
    !form.value.activity.trim() ||
    !Number.isInteger(form.value.day_number) ||
    form.value.day_number < 1 ||
    !Number.isInteger(form.value.sequence) ||
    form.value.sequence < 1
  ) {
    error.value = 'Enter an activity and valid day and sequence numbers.'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (editing.value) {
      await updateItineraryItem(
        selectedTourId.value,
        editing.value.id,
        form.value,
      )
    } else {
      await createItineraryItem(selectedTourId.value, form.value)
    }
    dialog.value = false
  } catch {
    error.value =
      'Unable to save itinerary item. Check that the day and sequence are unique.'
    loading.value = false
    return
  }

  try {
    await loadItems()
    success.value = editing.value
      ? 'Itinerary item updated.'
      : 'Itinerary item created.'
  } catch {
    items.value = []
    error.value = 'Itinerary item saved, but the list could not be refreshed.'
  } finally {
    loading.value = false
  }
}

function confirmDelete(item: ItineraryItem): void {
  deleting.value = item
  deleteDialog.value = true
}

async function remove(): Promise<void> {
  if (!deleting.value || !selectedTourId.value) return

  loading.value = true
  error.value = ''
  success.value = ''
  try {
    await deleteItineraryItem(selectedTourId.value, deleting.value.id)
    deleteDialog.value = false
  } catch {
    error.value = 'Unable to delete itinerary item.'
    loading.value = false
    return
  }

  try {
    await loadItems()
    success.value = 'Itinerary item deleted.'
  } catch {
    items.value = []
    error.value = 'Itinerary item deleted, but the list could not be refreshed.'
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
      <h1 class="text-h4">Itineraries</h1>
      <v-spacer />
      <v-btn
        v-if="canManageItineraries"
        color="primary"
        prepend-icon="mdi-plus"
        :disabled="!selectedTourId"
        @click="openCreate"
      >
        Add activity
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-select
      v-model="selectedTourId"
      label="Tour"
      :items="tours"
      item-title="title"
      item-value="id"
      :loading="loading"
      :disabled="loading"
      class="mb-4"
      @update:model-value="changeTour"
    />

    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-else-if="!tours.length" type="info" variant="tonal">
      No published tours are available to edit.
    </v-alert>
    <v-alert v-else-if="!items.length" type="info" variant="tonal">
      This tour has no itinerary items yet.
    </v-alert>
    <v-table v-else>
      <thead>
        <tr>
          <th>Day</th>
          <th>Sequence</th>
          <th>Activity</th>
          <th>Time</th>
          <th>Location</th>
          <th>Description</th>
          <th v-if="canManageItineraries" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>{{ item.day_number }}</td>
          <td>{{ item.sequence }}</td>
          <td>{{ item.activity }}</td>
          <td>{{ item.time || '-' }}</td>
          <td>{{ item.location || '-' }}</td>
          <td>{{ item.description || '-' }}</td>
          <td v-if="canManageItineraries">
            <v-btn
              size="small"
              variant="text"
              icon="mdi-pencil"
              :aria-label="`Edit ${item.activity}`"
              @click="openEdit(item)"
            />
            <v-btn
              size="small"
              variant="text"
              color="error"
              icon="mdi-delete-outline"
              :aria-label="`Delete ${item.activity}`"
              @click="confirmDelete(item)"
            />
          </td>
        </tr>
      </tbody>
    </v-table>

    <v-dialog v-model="dialog" max-width="650">
      <v-card>
        <v-card-title>
          {{ editing ? 'Edit itinerary item' : 'Add itinerary item' }}
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6">
              <v-text-field
                v-model.number="form.day_number"
                label="Day"
                type="number"
                min="1"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="form.sequence"
                label="Sequence"
                type="number"
                min="1"
              />
            </v-col>
          </v-row>
          <v-text-field
            v-model="form.activity"
            label="Activity"
            maxlength="255"
            required
          />
          <v-text-field
            v-model="form.time"
            label="Time"
            placeholder="For example, 08:00 or Morning"
            maxlength="50"
          />
          <v-text-field v-model="form.location" label="Location" maxlength="255" />
          <v-textarea
            v-model="form.description"
            label="Description"
            maxlength="10000"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="loading"
            @click="submit"
          >
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="480">
      <v-card>
        <v-card-title>Delete itinerary item?</v-card-title>
        <v-card-text>
          This will permanently remove
          <strong>{{ deleting?.activity }}</strong> from the itinerary.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Keep item</v-btn>
          <v-btn color="error" :loading="loading" @click="remove">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
