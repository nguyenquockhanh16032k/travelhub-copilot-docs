<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import {
  createAssignment,
  deleteAssignment,
  listAssignments,
  updateAssignment,
} from '../services/assignments'
import { listAdminDepartures } from '../services/departures'
import { listGuides } from '../services/guides'
import type {
  Guide,
  TourAssignment,
  TourAssignmentPayload,
} from '../types/operations'
import type { AdminDeparture } from '../types/catalog'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const canManageAssignments = computed(() =>
  hasPermission(auth.user?.roles, 'assignments:write'),
)
const departures = ref<AdminDeparture[]>([])
const guides = ref<Guide[]>([])
const assignments = ref<TourAssignment[]>([])
const selectedDeparture = ref<AdminDeparture | null>(null)
const departurePage = ref(1)
const departureTotal = ref(0)
const assignmentPage = ref(1)
const assignmentTotal = ref(0)
const pageSize = 20
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const deleteDialog = ref(false)
const editing = ref<TourAssignment | null>(null)
const deleting = ref<TourAssignment | null>(null)
const form = ref<TourAssignmentPayload>({
  guide_id: '',
  role: '',
  status: '',
})

async function loadDepartures(): Promise<void> {
  const result = await listAdminDepartures(departurePage.value, pageSize)
  departures.value = result.items
  departureTotal.value = result.total
}

async function loadAssignments(): Promise<void> {
  if (!selectedDeparture.value) {
    assignments.value = []
    assignmentTotal.value = 0
    return
  }
  const result = await listAssignments(
    selectedDeparture.value.id,
    assignmentPage.value,
    pageSize,
  )
  assignments.value = result.items
  assignmentTotal.value = result.total
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadDepartures(), loadAssignments()])
  } catch {
    error.value = 'Unable to load departures or guide assignments.'
  } finally {
    loading.value = false
  }
}

async function selectDeparture(departure: AdminDeparture): Promise<void> {
  selectedDeparture.value = departure
  assignmentPage.value = 1
  loading.value = true
  error.value = ''
  try {
    await loadAssignments()
  } catch {
    assignments.value = []
    error.value = 'Unable to load assignments for this departure.'
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editing.value = null
  form.value = { guide_id: '', role: '', status: '' }
  dialog.value = true
}

function openEdit(assignment: TourAssignment): void {
  editing.value = assignment
  form.value = {
    guide_id: assignment.guide_id,
    role: assignment.role,
    status: assignment.status,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  if (
    !selectedDeparture.value ||
    !form.value.guide_id ||
    !form.value.role.trim() ||
    !form.value.status.trim()
  ) {
    error.value = 'Choose a guide and enter a role and status.'
    return
  }
  loading.value = true
  error.value = ''
  success.value = ''
  const payload = {
    ...form.value,
    role: form.value.role.trim(),
    status: form.value.status.trim(),
  }
  const successMessage = editing.value
    ? 'Assignment updated.'
    : 'Guide assigned to departure.'
  try {
    if (editing.value) {
      await updateAssignment(
        selectedDeparture.value.id,
        editing.value.id,
        payload,
      )
    } else {
      await createAssignment(selectedDeparture.value.id, payload)
    }
    dialog.value = false
  } catch {
    error.value = 'Unable to save assignment.'
    loading.value = false
    return
  }
  try {
    await loadAssignments()
    success.value = successMessage
  } catch {
    assignments.value = []
    assignmentTotal.value = 0
    error.value = 'Assignment saved, but the list could not be refreshed.'
  } finally {
    loading.value = false
  }
}

function confirmDelete(assignment: TourAssignment): void {
  deleting.value = assignment
  deleteDialog.value = true
}

async function remove(): Promise<void> {
  if (!selectedDeparture.value || !deleting.value) return
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    await deleteAssignment(selectedDeparture.value.id, deleting.value.id)
    deleteDialog.value = false
    deleting.value = null
  } catch {
    loading.value = false
    error.value = 'Unable to remove assignment.'
    return
  }
  try {
    await loadAssignments()
    success.value = 'Assignment removed.'
  } catch {
    assignments.value = []
    assignmentTotal.value = 0
    error.value = 'Assignment removed, but the list could not be refreshed.'
  } finally {
    loading.value = false
  }
}

async function loadGuides(search?: string | null): Promise<void> {
  try {
    const result = await listGuides(1, 100, search ?? undefined)
    guides.value = result.items
  } catch {
    error.value = 'Unable to load guides.'
  }
}

onMounted(() => {
  void Promise.all([load(), loadGuides()])
})
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Tour assignments</h1>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <h2 class="text-h6 mb-2">Departures</h2>
    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert
      v-if="!loading && !departures.length"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      No departures found.
    </v-alert>
    <v-table v-else-if="departures.length" class="mb-2">
      <thead>
        <tr>
          <th>Tour</th>
          <th>Dates</th>
          <th>Status</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="departure in departures" :key="departure.id">
          <td>{{ departure.tour_title }}</td>
          <td>{{ departure.start_date }} – {{ departure.end_date }}</td>
          <td>{{ departure.status }}</td>
          <td>
            <v-btn
              size="small"
              variant="text"
              @click="selectDeparture(departure)"
            >
              Manage
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    <v-pagination
      v-if="departureTotal > pageSize"
      v-model="departurePage"
      :length="Math.ceil(departureTotal / pageSize)"
      :disabled="loading"
      @update:model-value="load"
    />

    <template v-if="selectedDeparture">
      <div class="d-flex align-center mt-8 mb-2">
        <div>
          <h2 class="text-h6">Assignments</h2>
          <div class="text-body-2">
            {{ selectedDeparture.tour_title }} ·
            {{ selectedDeparture.start_date }} ·
            {{ selectedDeparture.status }}
          </div>
        </div>
        <v-spacer />
        <v-btn
          v-if="canManageAssignments"
          color="primary"
          prepend-icon="mdi-plus"
          :disabled="!guides.length"
          @click="openCreate"
        >
          Assign guide
        </v-btn>
      </div>
      <v-alert
        v-if="!guides.length"
        type="info"
        variant="tonal"
        class="mb-4"
      >
        Add a guide before creating an assignment.
      </v-alert>
      <v-alert
        v-if="!loading && !assignments.length"
        type="info"
        variant="tonal"
      >
        No guides are assigned to this departure.
      </v-alert>
      <v-table v-else-if="assignments.length">
        <thead>
          <tr>
            <th>Guide</th>
            <th>Role</th>
            <th>Status</th>
            <th v-if="canManageAssignments" />
          </tr>
        </thead>
        <tbody>
          <tr v-for="assignment in assignments" :key="assignment.id">
            <td v-if="canManageAssignments">
              {{ assignment.guide.full_name }}
              <span v-if="assignment.guide.email">
                · {{ assignment.guide.email }}
              </span>
            </td>
            <td>{{ assignment.role }}</td>
            <td>{{ assignment.status }}</td>
            <td>
              <v-btn size="small" variant="text" @click="openEdit(assignment)">
                Edit
              </v-btn>
              <v-btn
                size="small"
                color="error"
                variant="text"
                @click="confirmDelete(assignment)"
              >
                Remove
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-pagination
        v-if="assignmentTotal > pageSize"
        v-model="assignmentPage"
        :length="Math.ceil(assignmentTotal / pageSize)"
        :disabled="loading"
        @update:model-value="loadAssignments"
      />
    </template>

    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editing ? 'Edit assignment' : 'Assign guide' }}
        </v-card-title>
        <v-card-text>
          <v-autocomplete
            v-model="form.guide_id"
            :items="guides"
            item-title="full_name"
            item-value="id"
            label="Guide"
            @update:search="loadGuides"
          />
          <v-text-field v-model="form.role" label="Role" required />
          <v-text-field v-model="form.status" label="Status" required />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="loading" @click="submit">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="450">
      <v-card>
        <v-card-title>Remove assignment?</v-card-title>
        <v-card-text>
          This removes {{ deleting?.guide.full_name }} from this departure.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="loading" @click="remove">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
